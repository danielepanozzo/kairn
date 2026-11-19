#!/usr/bin/env python3
"""reference.py [--check]: write the reference pages of the site, docs/reference/, from the data
the rest of the repository produces. Python 3 standard library only.

  python3 docs/tools/reference.py           write docs/reference/index.md, one page per kernel,
                                             and the Reference section of the nav in mkdocs.yml
  python3 docs/tools/reference.py --check   change nothing; exit 1 if a page or the nav differs
                                             from what would be written, or a stray page is there

Inputs, and nothing else:

- gen/claims.json: what each kernel claims, its status, theorem, source and per-format constants;
- gen/kernels/NAME.kernel: the limb names of the inputs and outputs, and the listing;
- include/kairn/gen/bounds.hpp: the constants that kairn::traits exports, as compiled;
- proofs/gen/Statements.v: each kernel's statement as Rocq reads it; and the theorem file each
  proved kernel names, to check that it has that theorem;
- results/*/brute/*.json: the stored summaries of the latest brute-force runs;
- docs/tools/reference_operations.py: which public operation calls which kernel (hand-written).

Every number, status and formula on a page is printed from these. A claim whose kind, field or
vocabulary this script does not know is an error, never a guess: a new kind needs its template
written here first (render_ensures, render_requires and their neighbors).
"""
import argparse
import decimal
import fractions
import json
import os
import re
import sys

# --- The switch for kernels this script cannot render yet --------------------------------------
#
# Kernels with "domain": "extended" (the full kernels *_full, the constructors make_* and
# ball_make_*, and the kernels that gain an IEEE-model statement; docs/developer/architecture.md,
# "Claims of the non-finite layer") have claims this script has no templates for: the kinds
# extends, represents and makes_ball, the requirements canonical() and ball(), and new meanings of
# the old kinds. With "fail", their presence in gen/claims.json is an error that names them, so
# that their templates get written before the pages are regenerated. With "skip", their pages are
# not written, the index lists them under "Not in this reference yet", and the script says so on
# standard error.
EXTENDED_DOMAIN = "fail"

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
REPO_URL = "https://github.com/danielepanozzo/kairn"
OUT_DIR = "docs/reference"
HAND_WRITTEN = {"reading.md"}          # pages of docs/reference/ that this script does not own
NAV_BEGIN = "  # BEGIN reference: written by docs/tools/reference.py; do not edit by hand"
NAV_END = "  # END reference"

# The two formats of the library: the C++ type and the precision p of each.
FORMATS = [("binary64", "double", 53), ("binary32", "float", 24)]

KNOWN_KERNEL_FIELDS = {"name", "inputs", "outputs", "value", "requires", "ensures", "min_precision",
                       "status", "theorem", "source", "flops", "instances", "domain"}
KNOWN_KINDS = {"normalized", "error", "leading_rounded", "rounded", "upper", "predicate", "encloses"}
KNOWN_REQUIRES = {"normalized", "abs_ge", "nonneg", "power_of_two"}
KNOWN_STATUS = {"proved", "unverified"}
KNOWN_WHEN = {None, "product_large"}
KNOWN_MODES = {"nearest": "RN", "down": "RD", "up": "RU"}
KNOWN_RELS = {"lt": "<", "le": "\\le", "eq": "="}


class ReferenceError(Exception):
    """A datum the pages cannot be printed from: the message says which and why."""


def fail(msg):
    raise ReferenceError(msg)


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read().replace("\r\n", "\n")   # a checkout with CRLF line ends is still fresh


# --- Expressions ----------------------------------------------------------------------------------
#
# The claims write values as expressions over input names (`x+y`, `abs(x)`, `cx*a`) and the
# constant c of an error bound as a rational expression in u (`3/(1-4*u)`). Both are parsed here,
# never evaluated, and printed as TeX.

def tokenize(text, where):
    tokens = re.findall(r"\s*([A-Za-z_][A-Za-z0-9_]*|\d+|[-+*/()])", text)
    if "".join(tokens) != re.sub(r"\s+", "", text):
        fail("%s: cannot read the expression %r" % (where, text))
    return tokens


def parse(text, where, names=None):
    """An expression into a tree: ('num', Fraction), ('name', s), ('neg', e), ('abs', e),
    ('+' | '-' | '*' | '/', a, b). Names are checked against `names` when it is given."""
    tokens = tokenize(text, where)
    pos = [0]

    def peek():
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def take(expected=None):
        tok = peek()
        if tok is None or (expected is not None and tok != expected):
            fail("%s: unexpected end or token in %r" % (where, text))
        pos[0] += 1
        return tok

    def expr():
        node = term()
        while peek() in ("+", "-"):
            op = take()
            node = (op, node, term())
        return node

    def term():
        node = factor()
        while peek() in ("*", "/"):
            op = take()
            node = (op, node, factor())
        return node

    def factor():
        tok = take()
        if tok == "-":
            return ("neg", factor())
        if tok == "(":
            node = expr()
            take(")")
            return node
        if tok.isdigit():
            return ("num", fractions.Fraction(int(tok)))
        if tok == "abs" and peek() == "(":
            take("(")
            node = expr()
            take(")")
            return ("abs", node)
        if names is not None and tok not in names:
            fail("%s: the name %r in %r is not one of %s" % (where, tok, text, sorted(names)))
        return ("name", tok)

    node = expr()
    if peek() is not None:
        fail("%s: cannot read the expression %r" % (where, text))
    return node


def name_tex(name):
    """x -> x, x0 -> x_0, cx -> c_x, cz0 -> c_{z0}."""
    m = re.fullmatch(r"([a-z])([a-z]?)(\d*)", name)
    if not m:
        fail("no TeX form for the name %r" % name)
    base, sub, digits = m.groups()
    sub = sub + digits
    if not sub:
        return base
    return "%s_%s" % (base, sub if len(sub) == 1 else "{%s}" % sub)


def num_tex(q, small=True):
    if q.denominator == 1:
        return str(q.numerator)
    sign = "-" if q < 0 else ""
    return "%s\\%sfrac{%d}{%d}" % (sign, "t" if small else "", abs(q.numerator), q.denominator)


PREC = {"+": 1, "-": 1, "*": 2, "/": 2, "neg": 3, "num": 4, "name": 4, "abs": 4}


def tex(node, parent=0, right=False):
    kind = node[0]
    if kind == "num":
        out = num_tex(node[1], small=False)
    elif kind == "name":
        out = name_tex(node[1])
    elif kind == "abs":
        out = "\\lvert %s\\rvert" % tex(node[1])
    elif kind == "neg":
        out = "-" + tex(node[1], PREC["neg"])
    elif kind == "/":
        return "\\frac{%s}{%s}" % (tex(node[1]), tex(node[2]))
    elif kind == "*":
        a, b = tex(node[1], 2), tex(node[2], 2, right=True)
        out = a + b if node[1][0] == "num" else a + " " + b
    else:
        out = "%s %s %s" % (tex(node[1], 1), node[0], tex(node[2], 1, right=True))
    p = PREC[kind]
    if p < parent or (right and p == parent and kind in ("+", "-")):
        out = "(%s)" % out
    return out


def is_name(node):
    return node[0] == "name"


# --- The data -------------------------------------------------------------------------------------

def load_claims(root):
    path = os.path.join(root, "gen", "claims.json")
    data = json.loads(read(path))
    if data.get("schema") != 1:
        fail("gen/claims.json has schema %r; this script reads schema 1" % data.get("schema"))
    return data["kernels"]


HEADER_KEYS = {"kernel", "input", "output", "value", "requires", "ensures", "min_precision", "theorem",
               "source", "license", "status", "cone_exempt", "ce_variant", "unused", "entry", "stored",
               "domain"}


def load_listing(root, name):
    """The description of a kernel: its leading comment, header fields and body lines."""
    path = os.path.join(root, "gen", "kernels", name + ".kernel")
    if not os.path.exists(path):
        fail("kernel %s: gen/kernels/%s.kernel does not exist" % (name, name))
    comment, header, body = [], [], []
    for line in read(path).split("\n"):
        m = re.match(r"([a-z_]+):\s+(.*)$", line)
        if line.startswith("#") and not header and not body:
            comment.append(line)
        elif m and m.group(1) in HEADER_KEYS and not body:
            header.append((m.group(1), m.group(2).strip()))
        elif line.strip():
            body.append(line.rstrip())
    limbs = {}
    for key, value in header:
        if key in ("input", "output"):
            m = re.fullmatch(r"(?:mask\s+)?([a-z][a-z0-9]*)(?:\s*=\s*(.+))?", value)
            if not m:
                fail("kernel %s: cannot read the line %s: %s" % (name, key, value))
            limbs[m.group(1)] = m.group(2).split() if m.group(2) else [m.group(1)]
    return {"comment": comment, "header": header, "body": body, "limbs": limbs,
            "fields": dict(header)}


def load_bounds(root):
    """kairn::gen::bounds as compiled: {(kernel, ctype): {field: literal}}."""
    text = read(os.path.join(root, "include", "kairn", "gen", "bounds.hpp"))
    out = {}
    for m in re.finditer(r"template <> struct (\w+)<(double|float)> \{(.*?)\n\};", text, re.S):
        fields = dict(re.findall(r"static constexpr \w+(?:::\w+)? (\w+) = ([^;]+);", m.group(3)))
        out[(m.group(1), m.group(2))] = fields
    return out


def load_statements(root):
    """{kernel: the text of its generated statement K_spec} from proofs/gen/Statements.v."""
    text = read(os.path.join(root, "proofs", "gen", "Statements.v"))
    out = {}
    for m in re.finditer(r"^Definition (\w+)_spec : Prop :=\n(?:.+\n)*", text, re.M):
        out[m.group(1)] = m.group(0).rstrip("\n")
    return out


def load_operations(root):
    """docs/tools/reference_operations.py of this root, as a module (loaded from its path, so that
    a test can point at a copy)."""
    import importlib.util
    path = os.path.join(root, "docs", "tools", "reference_operations.py")
    spec = importlib.util.spec_from_file_location("reference_operations_%d" % id(path), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def natural_key(text):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", text)]


def load_brute(root):
    """The summaries of the latest brute-force runs: those under results/NAME/brute/ with the
    last NAME in natural order (milestone2 after milestone1, milestone10 after milestone2)."""
    base = os.path.join(root, "results")
    dirs = sorted((d for d in (os.listdir(base) if os.path.isdir(base) else [])
                   if os.path.isdir(os.path.join(base, d, "brute"))), key=natural_key)
    for d in reversed(dirs):
        files = sorted(f for f in os.listdir(os.path.join(base, d, "brute")) if f.endswith(".json"))
        docs = []
        for f in files:
            data = json.loads(read(os.path.join(base, d, "brute", f)))
            if data.get("kairn_brute_summary") != 1:
                fail("results/%s/brute/%s is not a brute-force summary of version 1" % (d, f))
            docs.append(data)
        if docs:
            return {"name": d, "dir": "results/%s/brute" % d, "docs": docs}
    return None


# --- Claims as text -------------------------------------------------------------------------------

class Kernel:
    """One kernel of gen/claims.json, with what the pages need to print it."""

    def __init__(self, entry, listing):
        self.entry = entry
        self.name = entry["name"]
        self.listing = listing
        unknown = set(entry) - KNOWN_KERNEL_FIELDS
        if unknown:
            fail("kernel %s: gen/claims.json has fields this script does not know: %s; write what "
                 "the reference pages say about them in docs/tools/reference.py first"
                 % (self.name, ", ".join(sorted(unknown))))
        self.inputs = [i["name"] for i in entry["inputs"]]
        self.outputs = [o["name"] for o in entry["outputs"]]
        self.names = set(self.inputs) | set(self.outputs)
        for n in self.inputs + self.outputs:
            if n not in listing["limbs"]:
                fail("kernel %s: %s is not declared in gen/kernels/%s.kernel" % (self.name, n, self.name))
        if entry["status"] not in KNOWN_STATUS:
            fail("kernel %s: the status %r is not one this script knows (%s)"
                 % (self.name, entry["status"], ", ".join(sorted(KNOWN_STATUS))))
        self.proved = entry["status"] == "proved"
        self.value = parse(entry["value"], "kernel %s, value" % self.name, set(self.inputs))
        for e in entry["ensures"]:
            if e.get("kind") not in KNOWN_KINDS:
                fail("kernel %s: the claim kind %r has no template in docs/tools/reference.py; "
                     "write one (render_ensures and its neighbors) before regenerating the pages"
                     % (self.name, e.get("kind")))
        self.errors = [e for e in entry["ensures"] if e["kind"] == "error"]
        for fmt, _, _ in FORMATS:
            if len(entry["instances"].get(fmt, [])) != len(self.errors):
                fail("kernel %s: %s has %d constants for %d error claims"
                     % (self.name, fmt, len(entry["instances"].get(fmt, [])), len(self.errors)))

    def limbs(self, name):
        return self.listing["limbs"][name]

    def expanded(self, name):
        """Whether an output is written as the sum of its limbs: when it has several and every
        input has one (an error-free transformation returns a pair, which has no name in the
        statement)."""
        return (name in self.outputs and len(self.limbs(name)) > 1
                and all(len(self.limbs(i)) == 1 for i in self.inputs))

    def out_tex(self, name):
        if self.expanded(name):
            return " + ".join(name_tex(l) for l in self.limbs(name))
        return name_tex(name)

    def value_of(self, name):
        """name = name_0 + name_1, for a name of several limbs."""
        limbs = self.limbs(name)
        return "%s = %s" % (name_tex(name), " + ".join(name_tex(l) for l in limbs))

    def expr(self, text, where, names=None):
        return parse(text, "kernel %s, %s" % (self.name, where), names or self.names)

    # Requirements.
    def render_requires(self, req):
        m = re.fullmatch(r"(\w+)\(([^()]*)\)", req)
        if not m or m.group(1) not in KNOWN_REQUIRES:
            fail("kernel %s: the requirement %r has no template in docs/tools/reference.py"
                 % (self.name, req))
        kind, args = m.group(1), [a.strip() for a in m.group(2).split(",")]
        for a in args:
            if a not in self.inputs:
                fail("kernel %s: the requirement %r names %r, which is not an input" % (self.name, req, a))
        if kind == "normalized":
            (x,) = args
            limbs = self.limbs(x)
            if len(limbs) != 2:
                fail("kernel %s: normalized(%s) on %d limbs has no template" % (self.name, x, len(limbs)))
            return "$%s$ is normalized: $%s = \\mathrm{RN}(%s + %s)$" % (
                name_tex(x), name_tex(limbs[0]), name_tex(limbs[0]), name_tex(limbs[1]))
        if kind == "abs_ge":
            a, b = args
            return "$\\lvert %s\\rvert \\ge \\lvert %s\\rvert$" % (name_tex(a), name_tex(b))
        if kind == "nonneg":
            (a,) = args
            return "$%s \\ge 0$" % name_tex(a)
        (c,) = args
        return "$%s$ is a power of two: $%s = 2^n$ for an integer $n$" % (name_tex(c), name_tex(c))

    # Guarantees.
    def bound_tex(self, e):
        """The right-hand side of an error claim, or None when it is zero."""
        c = parse(e["c"], "kernel %s, c" % self.name, {"u"})
        k, t = e["k"], fractions.Fraction(e["t"])
        if not isinstance(k, int) or k < 1:
            fail("kernel %s: the exponent k=%r of an error claim is not a positive integer" % (self.name, k))
        uk = "u" if k == 1 else "u^%d" % k
        if e["form"] == "R":
            rho = "\\lvert %s\\rvert" % tex(self.value)
        elif e["form"] == "A":
            rho = "(%s)" % " + ".join("\\lvert %s\\rvert" % name_tex(i) for i in self.inputs)
        else:
            fail("kernel %s: the error form %r has no template" % (self.name, e["form"]))
        rel = None
        if c == ("num", 0):
            rel = None
        elif c[0] == "num":
            rel = (uk if c[1] == 1 else "%s\\,%s" % (num_tex(c[1]), uk)) + "\\," + rho
        elif c[0] == "/" and c[1][0] == "num" and c[1][1].denominator == 1:
            top = uk if c[1][1] == 1 else "%d%s" % (c[1][1], uk)
            rel = "\\frac{%s}{%s}\\," % (top, tex(c[2])) + rho
        else:
            rel = "\\left(%s\\right) %s\\," % (tex(c), uk) + rho
        tiny = None
        if t != 0:
            tiny = "\\eta" if t == 1 else "%s\\,\\eta" % num_tex(t)
        terms = [x for x in (rel, tiny) if x]
        return " + ".join(terms) if terms else None

    def when_tex(self, e):
        if e["when"] not in KNOWN_WHEN:
            fail("kernel %s: the condition when=%r has no template" % (self.name, e["when"]))
        if e["when"] == "product_large":
            v = tex(self.value)
            # 2^(2p-1) eta, written without p, which a kernel may use as a name (two_prod's product).
            return "when $%s = 0$ or $\\lvert %s\\rvert \\ge \\eta/(2u^2)$" % (v, v)
        return None

    def render_ensures(self, e, short=False):
        kind = e["kind"]
        if kind == "normalized":
            of = e["of"]
            limbs = self.limbs(of)
            if len(limbs) != 2:
                fail("kernel %s: normalized(%s) on %d limbs has no template" % (self.name, of, len(limbs)))
            if short:
                return "$%s$ normalized" % name_tex(of)
            return "$%s$ is normalized: $%s = \\mathrm{RN}(%s + %s)$" % (
                name_tex(of), name_tex(limbs[0]), name_tex(limbs[0]), name_tex(limbs[1]))
        if kind == "error":
            of, v = self.out_tex(e["of"]), tex(self.value)
            bound = self.bound_tex(e)
            when = self.when_tex(e)
            if bound is None:
                text = "$%s = %s$ exactly" % (of, v)
            else:
                left = "%s - %s" % (of, tex(self.value, 1, right=True))
                text = "$\\lvert %s\\rvert \\le %s$" % (left, bound)
            return text + (", " + when if when else "")
        if kind == "leading_rounded":
            limbs = self.limbs(e["of"])
            return "$%s = \\mathrm{RN}(%s)$" % (name_tex(limbs[0]), tex(self.value))
        if kind == "rounded":
            if e["mode"] not in KNOWN_MODES:
                fail("kernel %s: the rounding mode %r has no template" % (self.name, e["mode"]))
            text = "$%s = \\mathrm{%s}(%s)$" % (name_tex(e["of"]), KNOWN_MODES[e["mode"]], tex(self.value))
            if short:
                return text
            return text + {
                "nearest": ": the number of the format nearest to $%s$, ties to even",
                "down": ": the largest number of the format not above $%s$",
                "up": ": the smallest number of the format not below $%s$",
            }[e["mode"]] % tex(self.value)
        if kind == "upper":
            r, v = name_tex(e["of"]), tex(self.value)
            gaps = num_tex(fractions.Fraction(e["gaps"]))
            if short:
                return "$%s \\ge %s$, at most $%s$ gaps above" % (r, v, gaps)
            return ("$%s \\ge %s$, and $%s - (%s) \\le %s\\,(%s - \\mathrm{pred}(%s))$: at most %s gaps "
                    "of the format above the exact value" % (r, v, r, v, gaps, r, r, "$%s$" % gaps))
        if kind == "predicate":
            if e["rel"] not in KNOWN_RELS or len(e["args"]) != 2:
                fail("kernel %s: the predicate %r has no template" % (self.name, e["rel"]))
            a, b = (tex(self.expr(x, "predicate")) for x in e["args"])
            rel = "%s %s %s" % (a, KNOWN_RELS[e["rel"]], b)
            if short:
                return "exactly whether $%s$" % rel
            return "$%s$ is true exactly when $%s$, for the exact values" % (name_tex(e["of"]), rel)
        if kind == "encloses":
            balls = e["balls"]
            names = set(balls) | set(self.inputs)
            for b, cr in balls.items():
                if set(cr) != {"center", "radius"} or cr["center"] not in self.inputs or cr["radius"] not in self.inputs:
                    fail("kernel %s: the ball %r of an encloses claim is not a center and a radius of the inputs"
                         % (self.name, b))
            s = tex(self.expr(e["set"], "encloses", names))
            cz, rz = name_tex(e["center"]), name_tex(e["radius"])
            over = ", ".join("$\\lvert %s - %s\\rvert \\le %s$" % (name_tex(b), name_tex(cr["center"]),
                                                                    name_tex(cr["radius"]))
                             for b, cr in balls.items())
            if short:
                return "contains every $%s$" % s
            return ("$\\lvert %s - %s\\rvert \\le %s$ for all real %s with %s" % (
                "(%s)" % s if len(s) > 1 else s, cz, rz,
                " and ".join("$%s$" % name_tex(b) for b in balls), over))
        fail("kernel %s: the claim kind %r has no template" % (self.name, kind))

    def short(self):
        parts = [self.render_ensures(e, short=True) for e in self.entry["ensures"]
                 if e["kind"] != "normalized" and not (e["kind"] == "error" and e["when"])]
        normalized = [e for e in self.entry["ensures"] if e["kind"] == "normalized"]
        if normalized and parts:
            parts[-1] += ", normalized"
        return "; ".join(parts) or "; ".join(self.render_ensures(e, short=True) for e in self.entry["ensures"])

    def calls(self, known):
        """The kernels its listing calls, in order."""
        out = []
        for line in self.listing["body"]:
            for callee in re.findall(r"\b([a-z][a-z0-9_]*)\(", line):
                if callee in known and callee not in out:
                    out.append(callee)
        return out

    def constants_of(self):
        """The kernels whose unit_computed or tiny_computed the listing uses."""
        out = []
        for line in self.listing["body"]:
            for which, k in re.findall(r"const (unit_computed|tiny_computed)\((\w+)\)", line):
                if k not in out:
                    out.append(k)
        return out

    def label(self, e):
        """The oracle's label of an ensures entry, as the brute-force summaries print it."""
        kind = e["kind"]
        if kind == "error":
            return "error(%s) form %s, c=%s, k=%s, t=%s%s" % (
                e["of"], e["form"], e["c"], e["k"], e["t"], ", when %s" % e["when"] if e["when"] else "")
        if kind in ("normalized", "leading_rounded"):
            return "%s(%s)" % (kind, e["of"])
        if kind == "rounded":
            return "rounded(%s) %s" % (e["of"], e["mode"])
        if kind == "upper":
            return "upper(%s) gaps=%s" % (e["of"], e["gaps"])
        if kind == "predicate":
            return "predicate(%s) %s(%s)" % (e["of"], e["rel"], ", ".join(e["args"]))
        return "encloses(%s, %s) %s over %s" % (e["center"], e["radius"], e["set"], ", ".join(
            "%s=[%s +- %s]" % (b, cr["center"], cr["radius"]) for b, cr in e["balls"].items()))


# --- Numbers --------------------------------------------------------------------------------------

def fmt_int(n):
    return "{:,}".format(n).replace(",", " ")


def approx(q, digits=5):
    """A positive rational in scientific notation, correctly rounded to `digits` digits, as TeX."""
    ctx = decimal.Context(prec=digits)
    d = ctx.divide(decimal.Decimal(q.numerator), decimal.Decimal(q.denominator))
    mant, exp = format(d, ".%de" % (digits - 1)).split("e")
    mant = mant.rstrip("0").rstrip(".")
    return "%s \\times 10^{%d}" % (mant, int(exp))


def exact_tex(q):
    """A short exact form of a positive rational constant, when it has one: m 2^e, or
    n / (2^a + 2^b) and n / (2^a - 2^b) for a small n; otherwise None."""
    if q.denominator & (q.denominator - 1) == 0:
        m, e = q.numerator, -(q.denominator.bit_length() - 1)
        while m % 2 == 0 and m:
            m //= 2
            e += 1
        if m < 1 << 20:
            return ("2^{%d}" % e) if m == 1 else "%d \\cdot 2^{%d}" % (m, e)
    for n in range(1, 65):
        d = fractions.Fraction(n) / q
        if d.denominator != 1:
            continue
        d = d.numerator
        low = d & -d
        b = low.bit_length() - 1
        rest = d - low
        if rest and rest & (rest - 1) == 0:
            a = rest.bit_length() - 1
            return "\\frac{%d}{2^{%d} + 2^{%d}}" % (n, a, b)
        if (d + low) & (d + low - 1) == 0:
            a = (d + low).bit_length() - 1
            return "\\frac{%d}{2^{%d} - 2^{%d}}" % (n, a, b)
    return None


def constant_tex(text):
    q = fractions.Fraction(text)
    if q == 0:
        return "$0$"
    if q < 0:
        fail("a negative constant %s in gen/claims.json" % text)
    ex = exact_tex(q)
    return "$%s \\approx %s$" % (ex, approx(q)) if ex else "$\\approx %s$" % approx(q)


def short_dec(text, digits=6):
    d = decimal.Decimal(text)
    if d == 0:
        return "0"
    out = format(decimal.Context(prec=digits).create_decimal(d), "g")
    if d != 1 and decimal.Decimal(out) == 1:
        out = format(decimal.Context(prec=10).create_decimal(d), "g")
    return out


def near_one(text, attains):
    d = decimal.Decimal(text)
    return not attains and decimal.Decimal("0.99999999995") <= d <= 1


# --- Brute-force results --------------------------------------------------------------------------

def headline_field(kind):
    """(field, name, sign) of the statistic that says how close a claim came, or None."""
    return {"error": ("max_ratio", None, 1),
            "upper": ("maxima", "excess in gaps", 1),
            "encloses": ("minima", "slack in gaps of the radius", -1)}.get(kind)


def stat_of(entry, kind):
    h = headline_field(kind)
    if not h:
        return None
    v = entry.get(h[0])
    if v is not None and h[1] is not None:
        v = v.get(h[1])
    return v


def better(a, b, sign):
    if a is None:
        return b
    if b is None:
        return a
    return b if sign * (decimal.Decimal(b[0]) - decimal.Decimal(a[0])) > 0 else a


def merge(acc, entries, where):
    if acc is None:
        return [{"label": e["label"], "kind": e["kind"], "applicable": e.get("applicable", 0),
                 "failures": e.get("failures", 0), "stat": stat_of(e, e["kind"]),
                 "attains": bool(e.get("attains_claim")), "where": [where] if stat_of(e, e["kind"]) else []}
                for e in entries]
    if [a["label"] for a in acc] != [e["label"] for e in entries]:
        fail("the brute-force summaries judged different claims for one kernel: %s and %s"
             % ([a["label"] for a in acc], [e["label"] for e in entries]))
    for a, e in zip(acc, entries):
        a["applicable"] += e.get("applicable", 0)
        a["failures"] += e.get("failures", 0)
        a["attains"] = a["attains"] or bool(e.get("attains_claim"))
        h = headline_field(e["kind"])
        s = stat_of(e, e["kind"])
        if h and s:
            new = better(a["stat"], s, h[2])
            if new is s and new is not a["stat"]:
                a["where"] = [where]
            a["stat"] = new
    return acc


def brute_of(name, brute):
    """What the stored runs say about one kernel, merged over machines and runners."""
    if brute is None:
        return None
    rows, findings = [], []
    for fmt, ctype, _ in FORMATS:
        row = None
        for d in brute["docs"]:
            s = d["compiled"]["kernels"].get(name, {}).get(fmt)
            if not s:
                continue
            if row is None:
                row = {"title": "`%s` (`%s`), compiled" % (fmt, ctype), "machines": 0, "runners": 0,
                       "cases": 0, "judged": 0, "failed": 0, "invalid": 0, "entries": None, "ok": True}
            row["machines"] += 1
            row["runners"] += len(s["runners"])
            for key in ("cases", "judged", "failed", "invalid"):
                row[key] += s["counts"].get(key, 0)
            row["entries"] = merge(row["entries"], s["entries"], fmt)
            row["ok"] = row["ok"] and s.get("guards") == "ok"
        if row:
            rows.append(row)
    interp = None
    for d in brute["docs"]:
        for r in d["interp"]["enumerations"]:
            if r["kernel"] != name:
                continue
            if interp is None:
                interp = {"title": "toy formats, every operand", "domains": 0, "complete": 0, "formats": [],
                          "cases": 0, "judged": 0, "failed": 0, "invalid": 0, "entries": None, "ok": True}
            interp["domains"] += 1
            interp["complete"] += 1 if r.get("complete") else 0
            if r["format"] not in interp["formats"]:
                interp["formats"].append(r["format"])
            for key in ("cases", "judged", "failed", "invalid"):
                interp[key] += r.get("counts", {}).get(key, 0)
            if r.get("entries"):
                interp["entries"] = merge(interp["entries"], r["entries"], "`%s`" % r["format"])
            if r.get("complete"):
                interp["ok"] = interp["ok"] and r.get("guards") == "ok"
        for f in d.get("findings", []):
            key = (d["name"], f.get("part"), f.get("format"), tuple(f.get("why", [])))
            if f.get("kernel") == name and key not in [x[0] for x in findings]:
                findings.append((key, f))
    if interp:
        rows.append(interp)
    return {"rows": rows, "findings": findings} if rows or findings else None


# --- Pages ----------------------------------------------------------------------------------------

def code_tex(code):
    return "`%s`" % code


def operand_types(f):
    return ", ".join("`%s`" % t for t in f["operands"]) if f["operands"] else "none"


GENERATED = ("<!-- Generated by docs/tools/reference.py from gen/claims.json, gen/kernels/, "
             "include/kairn/gen/bounds.hpp, proofs/gen/Statements.v, %s and "
             "docs/tools/reference_operations.py. Do not edit: run python3 docs/tools/reference.py. -->")


class Site:
    def __init__(self, root, extended=None):
        self.root = root
        self.extended = extended or EXTENDED_DOMAIN
        if self.extended not in ("fail", "skip"):
            fail("EXTENDED_DOMAIN is %r; it is \"fail\" or \"skip\"" % self.extended)
        ops = load_operations(root)
        self.ops = ops
        self.groups = [(g, title, about) for g, title, about in ops.GROUPS]
        group_ids = {g for g, _, _ in self.groups}
        self.brute = load_brute(root)
        self.bounds = load_bounds(root)
        self.statements = load_statements(root)
        self.kernels, self.skipped = {}, []
        entries = load_claims(root)
        self.all_names = {e["name"] for e in entries}
        for entry in entries:
            name = entry["name"]
            domain = entry.get("domain", "finite")
            if domain == "extended":
                if self.extended == "fail":
                    fail("kernel %s has \"domain\": \"extended\", which this script cannot render yet: write its "
                         "templates in docs/tools/reference.py, or set EXTENDED_DOMAIN = \"skip\" there to "
                         "leave such kernels out of the reference for now" % name)
                self.skipped.append(name)
                continue
            if domain != "finite":
                fail("kernel %s: the domain %r is not one this script knows" % (name, domain))
            if name not in ops.KERNELS:
                fail("kernel %s is not in docs/tools/reference_operations.py: add its page there (group, "
                     "title, the C++ forms that reach it)" % name)
            self.kernels[name] = Kernel(entry, load_listing(root, name))
        for name, p in ops.KERNELS.items():
            if name not in self.all_names:
                fail("docs/tools/reference_operations.py names the kernel %s, which gen/claims.json does not have"
                     % name)
            if p["group"] not in group_ids:
                fail("docs/tools/reference_operations.py: %s is in the unknown group %r" % (name, p["group"]))
            for f in p["forms"]:
                if f["group"] and f["group"] not in group_ids:
                    fail("docs/tools/reference_operations.py: a form of %s is in the unknown group %r"
                         % (name, f["group"]))
        if self.skipped:
            sys.stderr.write("reference.py: not rendered, \"domain\": \"extended\" (EXTENDED_DOMAIN is \"skip\"): %s\n"
                             % ", ".join(self.skipped))
        self.callers = {}
        for k in self.kernels.values():
            for callee in k.calls(self.all_names):
                self.callers.setdefault(callee, []).append(k.name)
        for k in self.kernels.values():
            v = k.listing["fields"].get("ce_variant")
            if v:
                self.callers.setdefault(v, [])
        self.ce_of = {k.listing["fields"]["ce_variant"]: k.name for k in self.kernels.values()
                      if k.listing["fields"].get("ce_variant")}

    def generated(self):
        return GENERATED % ("%s/" % self.brute["dir"] if self.brute else "results/")

    def link(self, name, frm=""):
        if name in self.kernels:
            return "[`%s`](%s%s.md)" % (name, frm, name)
        return "`%s`" % name

    # One page per kernel.
    def page(self, name):
        k, p = self.kernels[name], self.ops.KERNELS[name]
        e = k.entry
        out = []
        w = out.append
        w("# %s" % p["title"])
        w("")
        w(self.generated())
        w("")
        status = "proved" if k.proved else "**UNVERIFIED**"
        w("Kernel `%s` · %s · [all operations](index.md) · [how to read this page](reading.md)" % (name, status))
        w("")
        if not k.proved:
            w("**UNVERIFIED: no proof is checked.** The statement below is a target: the oracle tests it, "
              "but Rocq has not checked a proof of it. An operation that calls this kernel compiles only "
              "with the marker `kairn::unverified` on an operand, and `kairn::traits` exports no constants "
              "for it ([What holds today](../getting-started/guarantees.md#proved-and-unverified)).")
            w("")

        # What it computes.
        w("## What it computes")
        w("")
        w(self.computes(k))
        w("")
        multi = [n for n in k.inputs + k.outputs if len(k.limbs(n)) > 1 and not k.expanded(n)]
        if multi:
            w("A number of several limbs stands for their exact sum: %s." % ", ".join(
                "$%s$" % k.value_of(n) for n in multi))
            w("")

        # The C++ forms.
        w("## C++")
        w("")
        if p["forms"]:
            w("| Form | Operands | Result | Note |")
            w("|---|---|---|---|")
            for f in p["forms"]:
                w("| `%s` | %s | `%s` | %s |" % (f["code"], operand_types(f), f["result"], f["note"] or ""))
            w("")
            constructors = [f for f in p["forms"] if re.match(r"(Expansion|Ball)<", f["code"])]
            w("`T` is `float` or `double`; the operations are in namespace `kairn`, header "
              "`kairn/kairn.hpp`. The operators and functions also accept the marker `kairn::unverified` "
              "on an operand, which they need while the kernel is UNVERIFIED%s." % (
                  " (a constructor does not take it)" if constructors else ""))
            if p["note"]:
                w("")
                w(p["note"])
        else:
            callers = self.callers.get(name, [])
            text = "No public operation computes this kernel on its own."
            if callers:
                text += " It is part of %s." % ", ".join(self.link(c) for c in callers)
            if name in self.ce_of:
                text += " It replaces %s in constant evaluation, where there is no fused multiply-add." % (
                    self.link(self.ce_of[name]))
            w(text)
        w("")

        # Requirements.
        w("## Requires")
        w("")
        w("- Every limb of every operand is a finite number of `T`.")
        for r in e["requires"]:
            w("- " + k.render_requires(r) + ".")
        w("")

        # Guarantees.
        w("## Guarantees" if k.proved else "## Target (not proved)")
        w("")
        w("When the requirements hold and no operation of the kernel overflows:")
        w("")
        for x in e["ensures"]:
            w("- " + k.render_ensures(x) + ".")
        w("")
        if any(k.bound_tex(x) is not None for x in k.errors):
            w(self.constants(k))
        users = k.constants_of()
        if users:
            w(self.ball_constants(k, users))
        w(self.precision(k))
        w("")

        # Status.
        w("## Status")
        w("")
        w(self.status(k))
        w("")

        # Source.
        w("## Source")
        w("")
        src = e["source"]
        w("**Algorithm:** %s. **License:** %s." % (self.cite(src["cite"]), src["license"]))
        w("")

        # Listing.
        w("## Listing")
        w("")
        w("From [`gen/kernels/%s.kernel`](%s/blob/main/gen/kernels/%s.kernel), the description the C++ "
          "and the formal model are generated from. Each line is one operation of `T`, rounded to "
          "nearest; `prod(a, b)` is $\\mathrm{RN}(ab)$, written as a fused multiply-add with a zero addend "
          "([the kernel IR](../developer/architecture.md#the-kernel-ir))." % (name, REPO_URL, name))
        calls = [c for c in k.calls(self.all_names)]
        if calls:
            w("It calls %s." % ", ".join(self.link(c) for c in calls))
        w("")
        w("```")
        for line in k.listing["comment"]:
            w(line)
        if k.listing["comment"]:
            w("")
        for line in k.listing["body"]:
            w(line)
        w("```")
        w("")

        # Measured.
        w("## Measured")
        w("")
        w(self.measured(k))

        # Not claimed.
        w("## Not claimed")
        w("")
        w("- Anything when an operand is infinite or NaN, or when an operation of the kernel overflows: "
          "what is proved and what is not written yet there is in "
          "[What holds today](../getting-started/guarantees.md#overflow-and-non-finite-values).")
        if any(r.startswith("normalized(") for r in e["requires"]):
            w("- Anything about an operand that is not normalized, which only `from_limbs_unchecked` or "
              "writing `limb[]` directly can make.")
        if not k.proved:
            w("- Anything at all, as a guarantee: the statement is a target until its proof is checked.")
        w("")
        return "\n".join(out)

    def computes(self, k):
        e = k.entry
        kinds = [x["kind"] for x in e["ensures"]]
        out = name_tex(k.outputs[0]) if len(k.outputs) == 1 else None
        v = tex(k.value)
        if "encloses" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "encloses")
            s = tex(k.expr(x["set"], "encloses", set(x["balls"]) | set(k.inputs)))
            over = ", ".join("%s \\in %s" % (name_tex(b), name_tex(b).upper()) for b in x["balls"])
            balls = " and ".join("$%s$ the ball of center $%s$ and radius $%s$" % (
                name_tex(b).upper(), name_tex(cr["center"]), name_tex(cr["radius"])) for b, cr in x["balls"].items())
            return ("A ball $Z$, of center $%s$ and radius $%s$, that contains $%s$ for every $%s$, with %s:"
                    "\n\n$$Z \\supseteq \\{\\, %s : %s \\,\\}.$$" % (
                        name_tex(x["center"]), name_tex(x["radius"]), s, over, balls, s, over))
        if "predicate" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "predicate")
            a, b = (tex(k.expr(y, "predicate")) for y in x["args"])
            return "Whether $%s %s %s$, for the exact values:\n\n$$%s = [\\, %s %s %s \\,].$$" % (
                a, KNOWN_RELS[x["rel"]], b, name_tex(x["of"]), a, KNOWN_RELS[x["rel"]], b)
        if "rounded" in kinds and len(k.outputs) == 1 and len(k.limbs(k.outputs[0])) == 1 and "error" not in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "rounded")
            return "$%s$ rounded to a number of `T`:\n\n$$%s = \\mathrm{%s}(%s).$$" % (
                v, out, KNOWN_MODES[x["mode"]], v)
        if "upper" in kinds:
            return "An upper bound of $%s$, a number of `T`:\n\n$$%s \\ge %s.$$" % (v, out, v)
        if len(k.outputs) != 1:
            fail("kernel %s: %d outputs, and no ball or predicate claim: no template" % (k.name, len(k.outputs)))
        out = k.out_tex(k.outputs[0])
        if k.errors and all(k.bound_tex(x) is None for x in k.errors):
            return "$%s$, exactly:\n\n$$%s = %s.$$" % (v, out, v)
        return "An approximation $%s$ of $%s$:\n\n$$%s \\approx %s.$$" % (out, v, out, v)

    def constants(self, k):
        out = []
        w = out.append
        proved = k.proved
        w("The constants of the bound%s, for each limb type, from `gen/claims.json`%s:" % (
            "" if proved else " (a target, not a guarantee)",
            "; `kairn::traits` exports them rounded up to `T`" if proved and self.ops.KERNELS[k.name]["traits"] else ""))
        w("")
        w("| | %s |" % " | ".join("`%s`" % ctype for _, ctype, _ in FORMATS))
        w("|---|" + "---|" * len(FORMATS))
        w("| unit roundoff $u$ | %s |" % " | ".join("$2^{-%d}$" % p for _, _, p in FORMATS))
        for i, x in enumerate(k.errors):
            cond = " (%s)" % k.when_tex(x) if x["when"] else ""
            if parse(x["c"], "kernel %s, c" % k.name, {"u"}) != ("num", 0):
                w("| relative term $c\\,u^%s$%s | %s |" % (x["k"], cond, " | ".join(
                    constant_tex(k.entry["instances"][fmt][i]["rel"]) for fmt, _, _ in FORMATS)))
            if fractions.Fraction(x["t"]) != 0:
                w("| absolute term $t\\,\\eta$%s | %s |" % (cond, " | ".join(
                    constant_tex(k.entry["instances"][fmt][i]["abs"]) for fmt, _, _ in FORMATS)))
        exported = [(ctype, self.bounds.get((k.name, ctype), {})) for _, ctype, _ in FORMATS]
        if proved and all("unit" in b for _, b in exported):
            w("| `unit`, `tiny`, as compiled | %s |" % " | ".join(
                "`%s`, `%s`" % (b["unit"], b["tiny"]) for _, b in exported))
            if all("unit_computed" in b for _, b in exported):
                w("| `unit_computed`, `tiny_computed` | %s |" % " | ".join(
                    "`%s`, `%s`" % (b["unit_computed"], b["tiny_computed"]) for _, b in exported))
        w("")
        traits = self.ops.KERNELS[k.name]["traits"]
        if proved and traits:
            w("The compiled constants are those of %s: `unit` and `tiny` bound the error relative to the "
              "exact result, `unit_computed` and `tiny_computed` relative to the computed one "
              "($\\lvert \\text{error}\\rvert \\le \\mathtt{unit\\_computed}\\,\\lvert\\text{computed}\\rvert"
              " + \\mathtt{tiny\\_computed}$)." % ", ".join(
                  "`kairn::%s`" % t + (" (also for `float`, `double` and `Expansion<T, 1>`)" if t.startswith("traits<T>") else "")
                  for t in traits))
            w("")
        return "\n".join(out)

    def ball_constants(self, k, users):
        rows = []
        for u in users:
            vals = []
            for _, ctype, _ in FORMATS:
                b = self.bounds.get((u, ctype), {})
                if "unit_computed" not in b:
                    fail("kernel %s uses the constants of %s, which include/kairn/gen/bounds.hpp does not export"
                         % (k.name, u))
                vals.append("`%s`, `%s`" % (b["unit_computed"], b["tiny_computed"]))
            rows.append("| %s | %s |" % (self.link(u), " | ".join(vals)))
        centers = [e["center"] for e in k.entry["ensures"] if e["kind"] == "encloses"]
        center = name_tex(centers[0]) if centers else "c"
        return ("The radius adds $U\\,\\lvert %s\\rvert + V$ for the rounding error of the center, where $U$ "
                "and $V$ are `unit_computed` and `tiny_computed` of the center's kernel: its proved bound "
                "relative to the computed value, rounded up to `T`. Every step of the radius is rounded up.\n\n"
                "| Center's kernel | $U$, $V$ for `%s` | for `%s` |\n|---|---|---|\n%s\n" % (
                    center, FORMATS[0][1], FORMATS[1][1], "\n".join(rows)))

    def precision(self, k):
        mp = k.entry["min_precision"]
        if mp is None:
            return ("The smallest precision for which the statement holds is not known yet; the oracle "
                    "judges every format.")
        if not isinstance(mp, int):
            fail("kernel %s: min_precision %r is not an integer" % (k.name, mp))
        short = [ctype for _, ctype, p in FORMATS if p < mp]
        types = ", ".join("`%s` has %d bits" % (ctype, p) for _, ctype, p in FORMATS)
        return ("%s for every binary format with a precision of at least %d bit%s and any exponent range, "
                "rounding to nearest with ties to even and with gradual underflow, in the model where no "
                "operation overflows. %s" % (
                    "Proved" if k.proved else "Stated", mp, "" if mp == 1 else "s",
                    "**Not covered: %s** (%s)." % (", ".join("`%s`" % c for c in short), types) if short
                    else "Both limb types qualify: %s." % types))

    def status(self, k):
        e = k.entry
        th = e.get("theorem")
        if k.proved:
            if not th or not th.get("file") or not th.get("name"):
                fail("kernel %s is proved but names no theorem" % k.name)
            path = os.path.join(self.root, th["file"])
            if not os.path.exists(path):
                fail("kernel %s: its theorem file %s does not exist" % (k.name, th["file"]))
            if not re.search(r"\b(Theorem|Lemma)\s+%s\b" % re.escape(th["name"]), read(path)):
                fail("kernel %s: %s has no theorem %s" % (k.name, th["file"], th["name"]))
            text = ("**Proved.** Rocq checks the theorem `%s`, in [`%s`](%s/blob/main/%s), against `%s_spec`, "
                    "the statement the generator prints from these claims into "
                    "[`proofs/gen/Statements.v`](%s/blob/main/proofs/gen/Statements.v); `make -C proofs` "
                    "finds no axiom in its proof beyond the four allowed ([Proofs](../proofs/index.md))." % (
                        th["name"], th["file"], REPO_URL, th["file"], k.name, REPO_URL))
        else:
            text = "**UNVERIFIED.** No proof of the statement is checked."
            if th and th.get("file") and th.get("name"):
                text += " The theorem is to be `%s`, in `%s`." % (th["name"], th["file"])
        spec = self.statements.get(k.name)
        if spec is None:
            fail("kernel %s: proofs/gen/Statements.v has no %s_spec; run python3 gen/kairn-gen build"
                 % (k.name, k.name))
        return (text + "\n\nThe statement, as Rocq reads it (the vocabulary, `fmt`, `RN`, `u`, `eta` and "
                "`normalized_2`, is defined at the top of the same file; `emin` is the exponent of $\\eta$ "
                "and `prec` the precision):\n\n```coq\n%s\n```" % spec)

    def cite(self, text):
        refs = os.path.join(self.root, "docs", "developer", "design", "phase0", "references.md")
        anchors = set(re.findall(r'<a id="([^"]+)"', read(refs))) if os.path.exists(refs) else set()

        def sub(m):
            key = m.group(0)
            if key.lower() in anchors:
                return "[%s](../developer/design/phase0/references.md#%s)" % (key, key.lower())
            return key
        return re.sub(r"\b[A-Z]{2,}\d{2}\b", sub, text)

    def measured(self, k):
        b = brute_of(k.name, self.brute)
        out = []
        w = out.append
        if b is None:
            w("No stored brute-force run has judged this kernel yet.")
            w("")
            return "\n".join(out)
        page = "docs/developer/results/brute-%s.md" % self.brute["name"]
        where = "the stored summaries in [`%s/`](%s/tree/main/%s)" % (self.brute["dir"], REPO_URL, self.brute["dir"])
        if os.path.exists(os.path.join(self.root, page)):
            where += " ([the report](../developer/results/brute-%s.md#%s))" % (self.brute["name"], k.name)
        w("The latest brute-force runs, from %s: the oracle judged, in exact arithmetic, the results of the "
          "compiled kernel (every compiler, scalar and packed code, every contraction setting) on random "
          "operands of `binary64` and `binary32`, and those of the generator's interpreter on every operand "
          "of small formats. A measurement, not a bound." % where)
        w("")
        current = [k.label(x) for x in k.entry["ensures"]]
        rows = b["rows"]
        judged_labels = next((r["entries"] for r in rows if r["entries"]), None)
        if judged_labels is not None and [x["label"] for x in judged_labels] != current:
            w("**These runs judged other claims.** They judged %s; the kernel now claims %s. Their numbers "
              "are not about the statement above." % (
                  "; ".join("`%s`" % x["label"] for x in judged_labels), "; ".join("`%s`" % c for c in current)))
            w("")
        cols = []
        for j, x in enumerate(k.entry["ensures"]):
            kind = x["kind"]
            if kind == "error":
                exact = k.bound_tex(x) is None
                cols.append((j, "largest error / bound" + (" (%s)" % ("when product large" if x["when"] else "always")
                                                          if len(k.errors) > 1 else ""), "exact" if exact else "ratio"))
            elif kind == "upper":
                cols.append((j, "largest excess, in gaps", "ratio"))
            elif kind == "encloses":
                cols.append((j, "smallest slack of the radius, in gaps", "slack"))
        head = ["Run", "Cases judged", "Failed"] + [c[1] for c in cols]
        if any(c[2] == "ratio" for c in cols):
            head.append("Bound attained")
        w("| " + " | ".join(head) + " |")
        w("|" + "---|" * len(head))
        for r in rows:
            if "machines" in r:
                title = "%s: %d runners on %d machine%s" % (r["title"], r["runners"], r["machines"],
                                                           "s" if r["machines"] > 1 else "")
            else:
                title = "%s: %d domain%s of %d format%s" % (r["title"], r["domains"], "s" if r["domains"] > 1 else "",
                                                            len(r["formats"]), "s" if len(r["formats"]) > 1 else "")
                if r["complete"] != r["domains"]:
                    title += " (%d stopped before the end%s)" % (
                        r["domains"] - r["complete"], ": see below" if b["findings"] else "")
            if not r["ok"]:
                title += " (**a guard failed**)"
            cells = [title, fmt_int(r["judged"]), fmt_int(r["failed"] + r["invalid"])]
            attained = []
            for j, _, how in cols:
                ent = r["entries"][j] if r["entries"] and j < len(r["entries"]) else None
                s = ent and ent["stat"]
                if not s:
                    cells.append("-")
                    continue
                if how == "exact":
                    cells.append("0 (exact)" if decimal.Decimal(s[0]) == 0 else short_dec(s[0]))
                    continue
                if how == "ratio" and near_one(s[0], ent["attains"]):
                    text = "1 − ε, ε < 10⁻⁹"
                else:
                    text = short_dec(s[0])
                if "formats" in r and ent["where"]:
                    text += " (%s)" % ent["where"][0]
                cells.append(text)
                if how == "ratio":
                    attained.append("yes" if ent["attains"] else "no")
            if any(c[2] == "ratio" for c in cols):
                cells.append(", ".join(attained) if attained else "-")
            w("| " + " | ".join(cells) + " |")
        w("")
        if any(c[2] == "slack" for c in cols):
            w("The slack is how far the returned radius is above the smallest radius that encloses the "
              "exact set, in units in the last place of the radius: below 1, a radius one unit smaller "
              "would not enclose it.")
            w("")
        for key, f in b["findings"]:
            w("A finding of the run on %s, %s `%s`: %s." % (
                key[0], {"interp": "the interpreter on"}.get(f.get("part"), f.get("part", "?")),
                f.get("format", "?"), "; ".join(f.get("why", []))))
            w("")
        return "\n".join(out)

    # The index.
    def index(self):
        out = []
        w = out.append
        w("# Reference")
        w("")
        w(self.generated())
        w("")
        proved = sorted(n for n, k in self.kernels.items() if k.proved)
        unverified = sorted(n for n, k in self.kernels.items() if not k.proved)
        w("Every public operation of Kairn, grouped by what it does, with the kernel that computes it. "
          "Each kernel has a page: its statement in plain mathematics, the C++ forms that reach it, what "
          "it requires, what is proved and with which theorem, its listing, and what the latest "
          "brute-force runs measured. [How to read a page](reading.md) explains each part.")
        w("")
        if unverified:
            w("Of the %d kernels, %d are proved and %d are **UNVERIFIED**: %s." % (
                len(self.kernels), len(proved), len(unverified), ", ".join(self.link(n) for n in unverified)))
        else:
            w("All %d kernels are proved: no operation needs the marker `kairn::unverified`." % len(self.kernels))
        w("")
        w("Notation: $u = 2^{-p}$ is the unit roundoff of the limb type `T` ($2^{-53}$ for `double`, "
          "$2^{-24}$ for `float`), $\\eta$ its smallest positive number, $\\mathrm{RN}$ rounding to nearest "
          "with ties to even, and a two-limb number $x = x_0 + x_1$ is *normalized* when "
          "$x_0 = \\mathrm{RN}(x_0 + x_1)$ ([Numbers](../developer/design/phase0/numbers.md#notation)). "
          "An operand of type `Expansion<T, 1>` next to an `Expansion<T, 2>` is converted to two limbs, "
          "exactly, and the two-limb form applies.")
        w("")
        for gid, title, about in self.groups:
            rows = []
            for name, p in self.ops.KERNELS.items():
                if name not in self.kernels:
                    continue
                k = self.kernels[name]
                forms = [f for f in p["forms"] if (f["group"] or p["group"]) == gid]
                if not forms and not (p["group"] == gid and not p["forms"]):
                    continue
                codes = []
                for f in forms:
                    if f["code"] not in codes:
                        codes.append(f["code"])
                ops = ", ".join("`%s`" % c for c in codes) if codes else "none (internal)"
                operands = operand_types(forms[0]) if forms else "-"
                status = "" if k.proved else " **UNVERIFIED**"
                rows.append("| %s | %s | %s | %s%s |" % (ops, operands, k.short(), self.link(name), status))
            for x in self.ops.EXACT:
                if x["group"] != gid:
                    continue
                for f in x["forms"]:
                    rows.append("| `%s` | %s | %s | none |" % (f["code"], operand_types(f), x["does"]))
            if not rows:
                continue
            w("## %s" % title)
            w("")
            w(about)
            w("")
            w("| C++ | Operands | What it gives | Kernel |")
            w("|---|---|---|---|")
            out.extend(rows)
            w("")
        if self.skipped:
            w("## Not in this reference yet")
            w("")
            w("These kernels of `gen/claims.json` have `\"domain\": \"extended\"`, whose claims this "
              "reference has no templates for yet: %s." % ", ".join("`%s`" % n for n in self.skipped))
            w("")
        return "\n".join(out)

    def nav(self):
        lines = [NAV_BEGIN, "  - Reference:", "      - reference/index.md", "      - How to read a page: reference/reading.md"]
        for gid, title, _ in self.groups:
            names = [n for n, p in self.ops.KERNELS.items() if p["group"] == gid and n in self.kernels]
            if not names:
                continue
            lines.append("      - %s:" % yaml_str(title))
            for n in names:
                lines.append("          - %s: reference/%s.md" % (yaml_str(self.ops.KERNELS[n]["title"]), n))
        lines.append(NAV_END)
        return lines

    def files(self):
        """{path relative to the root, with "/": content} of the pages."""
        out = {OUT_DIR + "/index.md": self.index() + "\n"}
        for name in self.kernels:
            out[OUT_DIR + "/" + name + ".md"] = self.page(name) + "\n"
        return out


def in_root(root, rel):
    return os.path.join(root, *rel.split("/"))


def yaml_str(text):
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9 ,'()-]*", text):
        return text
    return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"')


def with_nav(mkdocs_text, nav_lines):
    lines = mkdocs_text.split("\n")
    try:
        begin, end = lines.index(NAV_BEGIN), lines.index(NAV_END)
    except ValueError:
        fail("mkdocs.yml has no lines %r and %r around the Reference section of nav" % (NAV_BEGIN, NAV_END))
    if end < begin:
        fail("mkdocs.yml: the end of the Reference nav comes before its beginning")
    return "\n".join(lines[:begin] + nav_lines + lines[end + 1:])


def plan(root, extended=None):
    """{relative path: content} of every file the script owns, mkdocs.yml included."""
    site = Site(root, extended)
    files = site.files()
    mk = os.path.join(root, "mkdocs.yml")
    files["mkdocs.yml"] = with_nav(read(mk), site.nav())
    return files


def stray(root, files):
    d = in_root(root, OUT_DIR)
    if not os.path.isdir(d):
        return []
    owned = {p.rsplit("/", 1)[1] for p in files if p.startswith(OUT_DIR + "/")}
    return sorted(OUT_DIR + "/" + f for f in os.listdir(d)
                  if f.endswith(".md") and f not in owned and f not in HAND_WRITTEN)


def check(root, extended=None):
    """The differences between the committed files and what would be written, as messages."""
    files = plan(root, extended)
    problems = []
    for rel, text in sorted(files.items()):
        path = in_root(root, rel)
        if not os.path.exists(path):
            problems.append("%s is missing" % rel)
        elif read(path) != text:
            problems.append("%s differs from what docs/tools/reference.py writes" % rel)
    for rel in stray(root, files):
        problems.append("%s is not written by docs/tools/reference.py and is not a hand-written page "
                        "(HAND_WRITTEN)" % rel)
    return problems


def write(root, extended=None):
    files = plan(root, extended)
    os.makedirs(in_root(root, OUT_DIR), exist_ok=True)
    for rel in stray(root, files):
        os.remove(in_root(root, rel))
    for rel, text in files.items():
        with open(in_root(root, rel), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return len(files)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="change nothing; fail if a page or the nav is stale")
    a = ap.parse_args(argv)
    try:
        if a.check:
            problems = check(ROOT)
            for p in problems:
                print("reference.py: %s" % p)
            if problems:
                print("reference.py: run python3 docs/tools/reference.py and commit the result")
                return 1
            print("reference.py: the reference pages and the nav are fresh")
            return 0
        n = write(ROOT)
        print("reference.py: wrote %d files" % n)
        return 0
    except ReferenceError as e:
        print("reference.py: error: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
