#!/usr/bin/env python3
"""reference.py [--check]: write the reference pages of the site, docs/reference/, from the data
the rest of the repository produces. Python 3 standard library only.

  python3 docs/tools/reference.py           write docs/reference/index.md, one page per kernel,
                                             and the Reference section of the nav in mkdocs.yml
  python3 docs/tools/reference.py --check   change nothing; exit 1 if a page or the nav differs
                                             from what would be written, or a stray page is there
  python3 docs/tools/reference.py --claims PATH
                                             render every page from the claims in PATH, in memory,
                                             and write nothing (a trial of claims not committed)

Inputs, and nothing else:

- gen/claims.json: what each kernel claims, its statuses, theorems, source and per-format
  constants;
- gen/kernels/NAME.kernel: the limb names of the inputs and outputs, whether the public headers
  may call the kernel (`entry`), and the listing;
- include/kairn/gen/bounds.hpp: the constants that kairn::traits exports, as compiled;
- proofs/gen/Statements.v and Model.v: the generated statements, as Rocq reads them, and which
  kernels the generated model has; and the theorem file each proved statement names, to check
  that it has that theorem;
- proofs/audit/allowed_axioms.txt, the axioms the audit of `make -C proofs` allows, and the audit
  files (proofs/gen/Audit.v, proofs/gen/IeeeAudit.v, proofs/audit/HandAudit.v), to check that the
  audit prints the assumptions of every theorem a page calls proved. Which axioms each theorem
  depends on only Rocq computes: a page names the allowed ones and points to the artifact of the
  Proofs workflow, where the audit's output is kept, and never lists them per theorem;
- results/*/brute/*.json and results/*/brute/supplementary/*.json: the stored summaries of the
  brute-force runs, campaign by campaign; and results/brute-code.json, the fingerprints of the
  code and of the claims of every kernel at the commits those runs name (docs/tools/brute_code.py),
  which a page compares with those of include/kairn/gen/scalar.hpp, avx2.hpp, neon.hpp and
  prelude.hpp and of gen/claims.json: a run counts on a kernel's page only if it ran the code the
  kernel has now, and the page says when it judged other claims;
- docs/tools/reference_operations.py: which public operation calls which kernel (hand-written).

Every number, status and formula on a page is printed from these. A claim whose kind, field,
requirement or vocabulary this script does not know is an error, never a guess: a new kind needs
its template written here first (Kernel.finite_bullet, Site.extended_bullets and their
neighbors). The two readings of a claim, on finite operands and in the extended domain of
infinities and NaN, are those of docs/developer/architecture.md ("Claims", "Claims of the second
wave", "Claims of the non-finite layer").
"""
import argparse
import decimal
import fractions
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
REPO_URL = "https://github.com/danielepanozzo/kairn"
OUT_DIR = "docs/reference"
# Pages of docs/reference/ that this script does not own: these, and those of PAGES in
# docs/tools/reference_operations.py (hand_written()).
HAND_WRITTEN = {"reading.md"}
NAV_BEGIN = "  # BEGIN reference: written by docs/tools/reference.py; do not edit by hand"
NAV_END = "  # END reference"
# The page in place of which the CI puts Doxygen's C++ API reference (docs/Doxyfile).
API_PAGE = "api/index.md"

# The two formats of the library: the C++ type, the precision p, and q_max, the largest exponent
# of m 2^q (docs/developer/architecture.md, "Number formats"); 2^(q_max + p) is the overflow
# threshold.
FORMATS = [("binary64", "double", 53, 971), ("binary32", "float", 24, 104)]

KNOWN_KERNEL_FIELDS = {"name", "inputs", "outputs", "value", "requires", "ensures", "min_precision",
                       "status", "theorem", "source", "flops", "instances", "domain", "ieee_status",
                       "ieee_theorem", "ieee_only"}
KNOWN_GROUP_FIELDS = {"name", "limbs", "type"}
KNOWN_GROUP_TYPES = {"mask"}
KNOWN_DOMAINS = {"finite", "extended"}
KNOWN_STATUS = {"proved", "unverified"}
KNOWN_WHEN = {None, "product_large"}
KNOWN_MODES = {"nearest": "RN", "down": "RD", "up": "RU"}
KNOWN_RELS = {"lt": "<", "le": "\\le", "eq": "="}
KNOWN_LEADS = {"add": "+", "sub": "-", "mul": "\\cdot"}
KNOWN_CONDITION_FIELDS = {"abs_le", "exp"}
# The conditions of exact_when (architecture.md, "Claims of Milestone 2"): EXPR = 0 or |EXPR| > K,
# or >= K.
KNOWN_EXACT_CONDITIONS = {"zero_or_abs_gt": ">", "zero_or_abs_ge": "\\ge"}
KNOWN_SIDES = {"neighbor": {"up": ("succ", "above"), "down": ("pred", "below")},
               "bound": {"below": ("RD", "down"), "above": ("RU", "up")},
               "outward": {"below": ("RD", "down"), "above": ("RU", "up")},
               "set_bound": {"below": ("RD", "down"), "above": ("RU", "up")}}
# The tightness of an interval kernel and of a bound of a set (architecture.md, "Claims of the
# interval kernels").
KNOWN_TIGHT = {"exact": set(), "rounded": {"steps", "when"}, "outward": {"rel", "abs", "exact_when"}}
# The kinds whose entries name their own set, or make a value from the inputs: a kernel whose every
# entry is one of them has no value.
OWN_SET_KINDS = {"makes_ball", "makes_interval", "encloses_interval", "set_bound", "interval_set",
                 "ball_of_interval", "interval_of_ball", "splits", "certain", "trit", "ball_set", "ball_splits"}
# The set operations of interval_set and the special values of ball_of_interval (architecture.md,
# "Claims of the interval kernels: two limbs and the enclosure interface").
KNOWN_SET_OPERATIONS = {"union": ("\\cup", "hull"), "intersection": ("\\cap", "intersection")}
KNOWN_BALL_SPECIALS = {"ieee1788", "ball"}
# The relations of the predicates of sets, certain and trit (architecture.md, "Claims of the
# enclosure interface"): those of trit have a three-valued reading.
KNOWN_SET_RELATIONS = {"lt": 2, "le": 2, "eq": 2, "member": 2, "subset": 2, "equal": 2, "interior": 2,
                       "disjoint": 2, "empty": 1, "entire": 1}
KNOWN_TRIT_RELATIONS = {"lt", "le", "eq", "member"}

# The fields of each kind of `ensures` entry: required, optional in the extended domain.
KIND_FIELDS = {
    "normalized": ({"of"}, set()),
    "error": ({"of", "form", "c", "k", "t", "when"}, set()),
    "leading_rounded": ({"of"}, set()),
    "rounded": ({"of", "mode"}, set()),
    "upper": ({"of"}, set()),
    "holds": ({"rel", "args", "if"}, set()),
    "finite_or_nan": ({"of", "flag"}, set()),
    "predicate": ({"of", "rel", "args"}, set()),
    "encloses": ({"center", "radius", "set", "balls"}, {"finite_when"}),
    "extends": ({"of", "core", "lead", "finite_when"}, set()),
    "represents": ({"of"}, set()),
    "makes_ball": ({"center", "radius", "from"}, set()),
    "neighbor": ({"of", "side"}, set()),
    "bound": ({"of", "side", "steps"}, set()),
    # the larger of two expressions of the inputs and their limbs (the folds of maxima)
    "maximum": ({"of", "args"}, set()),
    # The interval kernels and the bounds of two limbs (architecture.md, "Claims of the interval
    # kernels").
    "outward": ({"of", "side", "rel", "abs"}, set()),
    "makes_interval": ({"lower", "upper", "from"}, set()),
    "encloses_interval": ({"lower", "upper", "set", "intervals", "tight", "bounded_when"}, set()),
    "set_bound": ({"of", "side", "set", "balls"}, set()),
    # Stage B1: the set operations, the conversions and the split of the enclosure interface.
    "interval_set": ({"lower", "upper", "set", "intervals"}, set()),
    "ball_of_interval": ({"center", "radius", "from", "special", "rel", "abs"}, set()),
    "interval_of_ball": ({"lower", "upper", "set", "balls", "tight"}, set()),
    "splits": ({"parts", "from"}, set()),
    # The predicates and comparisons of the enclosure interface: one mask, or yes and no.
    "certain": ({"of", "rel", "args"}, set()),
    "trit": ({"yes", "no", "rel", "args"}, set()),
    # The set operations of a ball.
    "ball_set": ({"center", "radius", "set", "balls"}, set()),
    "ball_splits": ({"parts", "from"}, set()),
}
# The fields an entry of these kinds has in either domain when it uses them (Milestone 2): a
# rounding under a condition, a condition of exactness, a zero factor, the midpoint of a ball made
# from an interval, an equivalence for a bounded result, a tightness, a value of its own (the
# accumulator's sum of magnitudes).
KIND_OPTIONAL = {"rounded": {"when", "zero_factor", "value"},
                 # the mask output that the conditions of exactness hold (the step of the scaling of a
                 # BallVector by a power of two)
                 "error": {"exact_when", "exact_flag"}, "encloses": {"exact_when"},
                 "bound": {"zero_factor"}, "outward": {"exact_when", "zero_factor"},
                 # the midpoint of a ball made from an interval; its center and radius (stage B2)
                 "makes_ball": {"midpoint_when", "rel", "abs", "smallest_radius"},
                 "encloses_interval": {"bounded_exactly", "zero_factor"}, "set_bound": {"tight"},
                 # the smallest radius; a radius finite under conditions (stage B2)
                 "ball_of_interval": {"smallest_radius", "finite_when"},
                 # the condition of a bounded result of two limbs (stage B2)
                 "interval_of_ball": {"bounded_when"},
                 # the sets of a predicate (intervals or balls, one of them), and its exactness
                 "certain": {"intervals", "balls", "exact", "exact_when"},
                 "trit": {"intervals", "balls", "exact", "exact_when"},
                 # gaps, or a value of its own (the exported bounds of the folds), under a mask (if); or
                 # when a mask input is false (unless), or the value exactly under conditions (exact_when:
                 # the radius of the scaling of a BallVector by a power of two)
                 "upper": {"gaps", "value", "if", "unless", "exact_when"},
                 # the finish of a fold of maxima: under a mask (if), the value stepped up (steps); of a
                 # constructor of a BallVector, the value also not negative (nonneg)
                 "finite_or_nan": {"if", "steps", "nonneg", "if_all"}}
# Which kinds and requirements each domain has a reading of.
DOMAIN_KINDS = {
    "finite": {"normalized", "error", "leading_rounded", "rounded", "upper", "predicate", "encloses",
               "neighbor", "bound", "holds", "maximum", "outward"},
    "extended": {"normalized", "error", "rounded", "upper", "predicate", "encloses", "extends",
                 "represents", "makes_ball", "neighbor", "bound", "finite_or_nan", "makes_interval",
                 "encloses_interval", "set_bound", "outward", "interval_set", "ball_of_interval", "interval_of_ball",
                 "splits", "certain", "trit", "ball_set", "ball_splits"},
}
DOMAIN_REQUIRES = {
    "finite": {"normalized", "abs_ge", "nonneg", "power_of_two", "count", "format", "at_most"},
    "extended": {"canonical", "ball", "nonneg", "power_of_two", "interval", "not_nan"},
}
# The kinds that exist only for a kernel without a statement on finite operands (a full kernel, a
# constructor, an interval kernel, the finish of a fold), which the claims mark "ieee_only": true;
# represents too, when it is the only entry.
IEEE_ONLY_KINDS = {"extends", "makes_ball", "finite_or_nan", "makes_interval", "encloses_interval", "set_bound",
                   "interval_set", "ball_of_interval", "interval_of_ball", "splits", "certain", "trit", "ball_set",
                   "ball_splits"}

# The one sentence every page with an UNVERIFIED statement about infinite and NaN operands carries,
# word for word: gen/claims.json is the only source of a status here.
IEEE_PROOFS_SENTENCE = ("The [Proofs](../proofs/index.md#what-is-proved-and-in-which-model) page says "
                        "which statements of the IEEE model are proved against statements written by "
                        "hand; this page gives the status that `gen/claims.json` gives.")

# The axiom audit: the allow-list, the files with one `Print Assumptions NAME.` per audited theorem,
# and where the CI keeps what the audit printed (.github/workflows/proofs.yml).
ALLOWED_AXIOMS = "proofs/audit/allowed_axioms.txt"
AUDIT_FILES = ["proofs/gen/Audit.v", "proofs/gen/IeeeAudit.v", "proofs/audit/HandAudit.v"]
PROOFS_WORKFLOW = REPO_URL + "/actions/workflows/proofs.yml"
AUDIT_ARTIFACT = "proof-audit"
NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
                9: "nine"}
# Every kernel's claims entry by name, for unit(K) and tiny(K) in the constants of a claim: filled
# by Site before the kernels are read.
KERNEL_CLAIMS = {}


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
    tokens = re.findall(r"\s*([A-Za-z_][A-Za-z0-9_]*|\d+|[-+*/()^])", text)
    if "".join(tokens) != re.sub(r"\s+", "", text):
        fail("%s: cannot read the expression %r" % (where, text))
    return tokens


def parse(text, where, names=None, constants=False):
    """An expression into a tree: ('num', Fraction), ('name', s), ('neg', e), ('abs', e),
    ('+' | '-' | '*' | '/', a, b), and in the expressions of constants of Milestone 2 ('^', e, n) for
    an integer power and ('call', 'unit' | 'tiny', K) for the constants of kernel K's bound, which only
    `constants` admits. Names are checked against `names` when it is given."""
    if not isinstance(text, str):
        fail("%s: %r is not an expression" % (where, text))
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
        node = atom(tok)
        if peek() == "^" and constants:
            take("^")
            sign = -1 if peek() == "-" and take("-") else 1
            n = take()
            if not n.isdigit():
                fail("%s: an exponent is an integer, in %r" % (where, text))
            node = ("^", node, sign * int(n))
        return node

    def atom(tok):
        if tok in ("unit", "tiny") and peek() == "(" and constants:
            take("(")
            kernel = take()
            take(")")
            return ("call", tok, kernel)
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


# The constants of a claim (rel and abs of `outward`, Milestone 2): the language of const up(EXPR)
# (u, eta, integers, unit(K), tiny(K), + - * /, integer powers ^) and up(EXPR) inside, the constant
# as the format rounds it (architecture.md, "Claims of the interval kernels"). Evaluated exactly
# here, per format, to print their values; never printed as formulas.

def claim_constant(text, where, fmt, kernels):
    """The exact value of a claim's constant in a format (p, q_min), as a Fraction; `kernels` maps
    a name to its claims entry, for unit(K) and tiny(K)."""
    p, qmin = fmt
    u, eta = fractions.Fraction(1, 2 ** p), fractions.Fraction(2) ** qmin
    tokens = re.findall(r"\s*([A-Za-z_][A-Za-z0-9_]*|\d+|[-+*/()^])", text)
    if "".join(tokens) != re.sub(r"\s+", "", text):
        fail("%s: cannot read the constant %r" % (where, text))
    pos = [0]

    def peek():
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def take(expected=None):
        tok = peek()
        if tok is None or (expected is not None and tok != expected):
            fail("%s: unexpected end or token in the constant %r" % (where, text))
        pos[0] += 1
        return tok

    def up(x):
        if x <= 0:
            fail("%s: up( ) of a value that is not positive in %r" % (where, text))
        e = x.numerator.bit_length() - x.denominator.bit_length()
        if fractions.Fraction(2) ** e > x:
            e -= 1
        q = fractions.Fraction(2) ** max(e - p + 1, qmin)
        return -((-x / q).__floor__()) * q

    def bound(fn, name):
        if name not in kernels:
            fail("%s: %s(%s) names a kernel that gen/claims.json does not have" % (where, fn, name))
        errs = [e for e in kernels[name]["ensures"] if e["kind"] == "error"]
        if len(errs) != 1:
            fail("%s: %s(%s) needs exactly one error claim of %s" % (where, fn, name, name))
        e = errs[0]
        if fn == "unit":
            return value(parse(e["c"], where, {"u"}), {"u": u}) * u ** e["k"]
        return fractions.Fraction(e["t"]) * eta

    def expr():
        x = term()
        while peek() in ("+", "-"):
            x = x + term() if take() == "+" else x - term()
        return x

    def term():
        x = unary()
        while peek() in ("*", "/"):
            x = x * unary() if take() == "*" else x / unary()
        return x

    def unary():
        if peek() == "-":
            take()
            return -unary()
        x = atom()
        if peek() == "^":
            take()
            sign = -1 if peek() == "-" and take() else 1
            n = take()
            if not n.isdigit():
                fail("%s: an exponent is an integer, in %r" % (where, text))
            x = x ** (sign * int(n))
        return x

    def atom():
        tok = take()
        if tok == "(":
            x = expr()
            take(")")
            return x
        if tok.isdigit():
            return fractions.Fraction(int(tok))
        if tok in ("unit", "tiny") and peek() == "(":
            take("(")
            name = take()
            take(")")
            return bound(tok, name)
        if tok == "up" and peek() == "(":
            take("(")
            x = expr()
            take(")")
            return up(x)
        if tok in ("u", "eta"):
            return u if tok == "u" else eta
        fail("%s: the name %r in the constant %r is not u, eta, unit( ), tiny( ) or up( )" % (where, tok, text))

    x = expr()
    if peek() is not None:
        fail("%s: cannot read the constant %r" % (where, text))
    return x


def value(node, env):
    """The exact value of a parsed expression, each name bound in env."""
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "name":
        return env[node[1]]
    if kind == "neg":
        return -value(node[1], env)
    if kind == "abs":
        return abs(value(node[1], env))
    a, b = value(node[1], env), value(node[2], env)
    return {"+": a + b, "-": a - b, "*": a * b}[kind] if kind != "/" else a / b


def substitute(node, mapping):
    """The tree with each name in mapping replaced by the name it maps to."""
    if node[0] == "name":
        return ("name", mapping.get(node[1], node[1]))
    if node[0] in ("num", "call"):
        return node
    return (node[0],) + tuple(substitute(n, mapping) if isinstance(n, tuple) else n for n in node[1:])


def sum_terms(node):
    """The terms of a value read as a sum: s + x y gives s and x y (a - b gives a and -b)."""
    if node[0] == "+":
        return sum_terms(node[1]) + sum_terms(node[2])
    if node[0] == "-":
        return sum_terms(node[1]) + [("neg", t) for t in sum_terms(node[2])]
    return [node]


def has_product(node):
    if node[0] == "*":
        return True
    return any(isinstance(n, tuple) and has_product(n) for n in node[1:])


def has_binary(node):
    """Whether a value has a sum, a difference or a product: a value of two operands."""
    if node[0] in ("+", "-", "*"):
        return True
    return any(isinstance(n, tuple) and has_binary(n) for n in node[1:])


def name_tex(name):
    """x -> x, x0 -> x_0, cx -> c_x, cz0 -> c_{z0}; eta, in the threshold of a condition, -> eta."""
    if name == "eta":
        return "\\eta"
    m = re.fullmatch(r"([a-z])([a-z]?)(\d*)", name)
    if name in ("ok", "no") or (not m and re.fullmatch(r"[a-z]{3,}", name)):
        # a word: the mask of an exported bound, the flag of a fold, the answers of a comparison
        return "\\mathit{%s}" % name
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


PREC = {"+": 1, "-": 1, "*": 2, "/": 2, "neg": 3, "num": 4, "name": 4, "abs": 4, "^": 4, "call": 4}


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
    elif kind == "^":
        base = tex(node[1]) if node[1][0] in ("num", "name", "call", "abs") else "(%s)" % tex(node[1])
        out = "%s^{%d}" % (base, node[2])
    elif kind == "call":
        out = "\\mathrm{%s}(\\mathtt{%s})" % (node[1], node[2].replace("_", "\\_"))
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


def parenthesized(node):
    """TeX of an expression, in parentheses unless it is one name."""
    return tex(node) if node[0] in ("name", "num", "abs") else "(%s)" % tex(node)


# --- The data -------------------------------------------------------------------------------------

def load_claims(root, path=None):
    """The kernels of gen/claims.json, or of another claims file (--claims)."""
    path = path or os.path.join(root, "gen", "claims.json")
    data = json.loads(read(path))
    if data.get("schema") != 1:
        fail("%s has schema %r; this script reads schema 1" % (path, data.get("schema")))
    return data["kernels"]


def load_listing(root, name):
    """The description of a kernel: its leading comment, header fields and body lines."""
    path = os.path.join(root, "gen", "kernels", name + ".kernel")
    if not os.path.exists(path):
        fail("kernel %s: gen/kernels/%s.kernel does not exist" % (name, name))
    # The layout of every description: comment lines, the header (one field per line), a blank
    # line, the body.
    comment, header, body = [], [], []
    state = "comment"
    for line in read(path).split("\n"):
        if state == "comment" and line.startswith("#"):
            comment.append(line)
            continue
        if state == "comment":
            state = "header"
        if state == "header":
            if not line.strip():
                state = "body"
                continue
            # A field the pages do not read (the generator's own: cone_exempt, guard_pending, ...) is
            # kept and ignored; the claims, not this header, are what the pages print.
            m = re.match(r"([a-z_]+):\s+(.*)$", line)
            if not m:
                fail("gen/kernels/%s.kernel: the header line %r is not a field" % (name, line))
            header.append((m.group(1), m.group(2).strip()))
        elif line.strip():
            body.append(line.rstrip())
    limbs = {}
    for key, value in header:
        if key in ("input", "output"):
            m = re.fullmatch(r"(?:(?:mask|stored|supplied)\s+)*([a-z][a-z0-9]*)(?:\s*=\s*(.+))?", value)
            if not m:
                fail("kernel %s: cannot read the line %s: %s" % (name, key, value))
            limbs[m.group(1)] = m.group(2).split() if m.group(2) else [m.group(1)]
    return {"comment": comment, "header": header, "body": body, "limbs": limbs,
            "fields": dict(header)}


def load_bounds(root):
    """kairn::gen::bounds as compiled: {(kernel, ctype): {field: literal}}."""
    text = read(os.path.join(root, "include", "kairn", "gen", "bounds.hpp"))
    out = {}
    for m in re.finditer(r"template <> struct (\w+)<(double|float)> \{(.*?)\};", text, re.S):
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


def strip_rocq_comments(text):
    """Rocq source without its comments, which nest."""
    out, depth, i = [], 0, 0
    while i < len(text):
        if text.startswith("(*", i):
            depth, i = depth + 1, i + 2
        elif depth and text.startswith("*)", i):
            depth, i = depth - 1, i + 2
        else:
            if not depth:
                out.append(text[i])
            i += 1
    return "".join(out)


def load_not_judged(root):
    """The kernels the oracle does not judge yet: the list KAIRN_NOT_YET_CROSS_CHECKED of
    tests/CMakeLists.txt, read as tests/brute/brute.py reads it (the words between
    `set(KAIRN_NOT_YET_CROSS_CHECKED` at the start of a line and the next `)`), empty when the file has
    none."""
    path = os.path.join(root, "tests", "CMakeLists.txt")
    if not os.path.exists(path):
        return set()
    m = re.search(r"^set\(KAIRN_NOT_YET_CROSS_CHECKED\s([^)]*)\)", read(path), re.M)
    return set(m.group(1).split()) if m else set()


def load_audit(root):
    """(allowed, audited): the axioms of the audit's allow-list, in its order, and {theorem: audit
    file} for every theorem whose assumptions an audit file prints. The allow-list is read as
    proofs/audit/audit.py reads it."""
    path = in_root(root, ALLOWED_AXIOMS)
    if not os.path.exists(path):
        fail("%s does not exist" % ALLOWED_AXIOMS)
    allowed = [l.strip() for l in read(path).split("\n") if l.strip() and not l.startswith("#")]
    if not allowed:
        fail("%s lists no axiom" % ALLOWED_AXIOMS)
    audited = {}
    for rel in AUDIT_FILES:
        p = in_root(root, rel)
        if not os.path.exists(p):
            fail("the audit file %s does not exist" % rel)
        for name in re.findall(r"Print\s+Assumptions\s+([\w.']+?)\s*\.(?:\s|$)", strip_rocq_comments(read(p))):
            audited.setdefault(name, rel)
    return allowed, audited


def load_operations(root):
    """docs/tools/reference_operations.py of this root, as a module (loaded from its path, so that
    a test can point at a copy)."""
    import importlib.util
    path = os.path.join(root, "docs", "tools", "reference_operations.py")
    spec = importlib.util.spec_from_file_location("reference_operations_%d" % id(path), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fold_kernels(root, fold, seen=()):
    """The names that gen/kernels/FOLD.fold calls in its step, records, combinations, radius, bound and
    finish, its check, and those of the folds it names as its centers or coefficients, in order."""
    path = os.path.join(root, "gen", "kernels", fold + ".fold")
    if fold in seen or not os.path.exists(path):
        return []
    out = []
    for line in read(path).split("\n"):
        m = re.match(r"(step|record|combine|radius|bound|finish|check|centers|coefficients):\s+(.*)", line)
        if not m:
            continue
        if m.group(1) in ("centers", "coefficients"):
            names = fold_kernels(root, m.group(2).strip(), seen + (fold,))
        elif m.group(1) == "check":
            names = [m.group(2).strip()]
        else:
            names = re.findall(r"=\s*([a-z][a-z0-9_]*)\(", m.group(2))
        out += [n for n in names if n not in out]
    return out


def natural_key(text):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", text)]


def load_brute(root):
    """The stored brute-force campaigns, oldest first: for each NAME with summaries under
    results/NAME/brute/, in natural order (milestone2 after milestone1, milestone10 after
    milestone2), those summaries and the ones of its supplementary runs, under
    results/NAME/brute/supplementary/: runs of a few kernels, at the commit of the campaign or a
    later one, whose rows a page shows apart. Each summary names the commits of the code it ran
    (`commit`); whether that is a kernel's code now, results/brute-code.json says (load_code)."""
    base = os.path.join(root, "results")
    dirs = sorted((d for d in (os.listdir(base) if os.path.isdir(base) else [])
                   if os.path.isdir(os.path.join(base, d, "brute"))), key=natural_key)

    def summaries(rel, part):
        path = os.path.join(base, *rel.split("/"))
        out = []
        for f in sorted(f for f in (os.listdir(path) if os.path.isdir(path) else []) if f.endswith(".json")):
            data = json.loads(read(os.path.join(path, f)))
            if data.get("kairn_brute_summary") != 1:
                fail("results/%s/%s is not a brute-force summary of version 1" % (rel, f))
            data["_path"] = "results/%s/%s" % (rel, f)
            data["_part"] = part
            out.append(data)
        return out
    out = []
    for d in dirs:
        docs = summaries(d + "/brute", "main")
        sup = summaries(d + "/brute/supplementary", "supplementary")
        if docs or sup:
            out.append({"name": d, "dir": "results/%s/brute" % d, "docs": docs, "supplementary": sup})
    return out


def brute_code_module():
    """docs/tools/brute_code.py, the fingerprints of the code of kernels, from beside this script."""
    import importlib.util
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brute_code.py")
    spec = importlib.util.spec_from_file_location("kairn_brute_code", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BRUTE_CODE = brute_code_module()
# The fingerprints of a tree's kernels, by the text of its generated headers: the tests render many
# pages from one tree.
CODE_CACHE = {}


def load_code(root, campaigns):
    """{commit: {kernel or loop: fingerprint of its code}} of results/brute-code.json, which must
    have every commit that a stored summary names."""
    try:
        code = BRUTE_CODE.load(root)
    except BRUTE_CODE.CodeError as e:
        fail(str(e))
    for c in campaigns:
        for d in c["docs"] + c["supplementary"]:
            if not d.get("commit"):
                fail("%s names no commit of the code it ran" % d["_path"])
            for commit in d["commit"]:
                if commit not in code:
                    fail("%s ran the code of commit %s, of which %s has no fingerprints: run python3 "
                         "docs/tools/brute_code.py in a clone with the history, and commit what it writes"
                         % (d["_path"], commit[:7], BRUTE_CODE.MANIFEST))
    return code


def code_now(root, kernels):
    """{kernel: fingerprint of its code in the tree under root}, from include/kairn/gen/."""
    files = {}
    for h in (BRUTE_CODE.PRELUDE,) + BRUTE_CODE.HEADERS:
        path = in_root(root, BRUTE_CODE.header_path(h))
        if not os.path.exists(path):
            fail("%s does not exist" % BRUTE_CODE.header_path(h))
        files[h] = read(path)
    key = (tuple(sorted(kernels)), tuple(files[h] for h in sorted(files)))
    if key not in CODE_CACHE:
        try:
            CODE_CACHE.clear()
            CODE_CACHE[key] = BRUTE_CODE.fingerprints(files, kernels, [])
        except BRUTE_CODE.CodeError as e:
            fail(str(e))
    return CODE_CACHE[key]


# --- One kernel -----------------------------------------------------------------------------------

class Kernel:
    """One kernel of gen/claims.json, checked against the vocabulary this script knows, with what
    the pages need to print its statement on finite operands."""

    def __init__(self, entry, listing):
        self.entry = entry
        self.name = entry["name"]
        self.listing = listing
        where = "kernel %s" % self.name
        unknown = set(entry) - KNOWN_KERNEL_FIELDS
        if unknown:
            fail("%s: gen/claims.json has fields this script does not know: %s; write what the reference "
                 "pages say about them in docs/tools/reference.py first" % (where, ", ".join(sorted(unknown))))
        for g in entry["inputs"] + entry["outputs"]:
            if set(g) - KNOWN_GROUP_FIELDS or g.get("type", "mask") not in KNOWN_GROUP_TYPES:
                fail("%s: the input or output %r has fields or a type this script does not know" % (where, g))
        self.inputs = [i["name"] for i in entry["inputs"]]
        self.mask_inputs = {i["name"] for i in entry["inputs"] if i.get("type") == "mask"}
        self.outputs = [o["name"] for o in entry["outputs"]]
        self.names = set(self.inputs) | set(self.outputs)
        for n in self.inputs + self.outputs:
            if n not in listing["limbs"]:
                fail("%s: %s is not declared in gen/kernels/%s.kernel" % (where, n, self.name))
        self.domain = entry.get("domain", "finite")
        if self.domain not in KNOWN_DOMAINS:
            fail("%s: the domain %r is not one this script knows" % (where, self.domain))
        self.extended = self.domain == "extended"
        if entry["status"] not in KNOWN_STATUS:
            fail("%s: the status %r is not one this script knows (%s)"
                 % (where, entry["status"], ", ".join(sorted(KNOWN_STATUS))))
        if self.extended:
            if entry.get("ieee_status") not in KNOWN_STATUS:
                fail("%s: a kernel of the extended domain has the ieee_status %r, not one this script knows"
                     % (where, entry.get("ieee_status")))
        elif "ieee_status" in entry or "ieee_theorem" in entry:
            fail("%s: a kernel of the finite domain has an ieee_status or an ieee_theorem" % where)
        self.proved = entry["status"] == "proved"
        self.ieee_proved = self.extended and entry["ieee_status"] == "proved"
        self.value = (parse(entry["value"], "%s, value" % where, set(self.inputs))
                      if "value" in entry else None)
        # Requirements, in the vocabulary of the domain.
        self.requires = []
        for req in entry["requires"]:
            m = re.fullmatch(r"(\w+)\(([^()]*)\)", req)
            if not m or m.group(1) not in DOMAIN_REQUIRES[self.domain]:
                fail("%s: the requirement %r has no template in docs/tools/reference.py for the %s domain"
                     % (where, req, self.domain))
            args = [a.strip() for a in m.group(2).split(",")]
            if m.group(1) == "format":                # format(half): about the format, not an input
                if args != ["half"]:
                    fail("%s: the requirement %r has no template" % (where, req))
                self.requires.append(("format", args))
                continue
            if m.group(1) == "at_most":               # at_most(g, 1): an input at most a positive integer
                if len(args) != 2 or args[0] not in self.inputs or not re.fullmatch(r"[1-9][0-9]*", args[1]):
                    fail("%s: the requirement %r has no template" % (where, req))
                self.requires.append(("at_most", args))
                continue
            for a in args:
                if a not in self.inputs:
                    fail("%s: the requirement %r names %r, which is not an input" % (where, req, a))
            if len(args) != {"abs_ge": 2, "ball": 2, "interval": 2}.get(m.group(1), 1):
                fail("%s: the requirement %r has the wrong number of arguments" % (where, req))
            self.requires.append((m.group(1), args))
        # Claims, in the vocabulary of the domain, with exactly the fields of their kind.
        for e in entry["ensures"]:
            kind = e.get("kind")
            if kind not in DOMAIN_KINDS[self.domain]:
                fail("%s: the claim kind %r has no template in docs/tools/reference.py for the %s domain; "
                     "write one before regenerating the pages" % (where, kind, self.domain))
            required, optional = KIND_FIELDS[kind]
            if self.domain == "finite":
                optional = set()
            optional = optional | KIND_OPTIONAL.get(kind, set())
            fields = set(e) - {"kind"}
            if not required <= fields or fields - required - optional:
                fail("%s: a %s claim has the fields %s; this script knows %s" % (
                    where, kind, sorted(fields), sorted(required | optional)))
            for c in e.get("finite_when", []):
                if set(c) != KNOWN_CONDITION_FIELDS or not isinstance(c["exp"], int):
                    fail("%s: the finite_when condition %r is not one this script knows" % (where, c))
                parse(c["abs_le"], "%s, finite_when" % where, set(self.inputs))
            if "exact_when" in e:
                self.exact_tex(e["exact_when"])          # every condition is one this script can print
            if kind == "rounded" and "when" in e and e["when"] not in KNOWN_WHEN - {None}:
                fail("%s: the condition when=%r of a rounded claim has no template" % (where, e["when"]))
            if kind in KNOWN_SIDES and e["side"] not in KNOWN_SIDES[kind]:
                fail("%s: the side %r of a %s claim has no template" % (where, e["side"], kind))
            if kind == "bound" and (not isinstance(e["steps"], int) or e["steps"] < 0):
                fail("%s: the steps %r of a bound claim are not an integer >= 0" % (where, e["steps"]))
            if kind == "upper" and "gaps" not in e and "value" not in e:
                fail("%s: an upper claim has gaps or a value of its own" % where)
            if kind == "upper" and "value" in e:
                self.expr(e["value"], "upper value", self.names | {"u", "eta"}, constants=True)
            if kind == "holds":
                for a in e["args"]:
                    self.expr(a, "holds", self.names | {"u", "eta"}, constants=True)
                if e["rel"] not in KNOWN_RELS:
                    fail("%s: the relation %r of a holds claim has no template" % (where, e["rel"]))
            if kind == "maximum":
                if len(e["args"]) != 2:
                    fail("%s: a maximum claim has two expressions" % where)
                for a in e["args"]:
                    self.limb_expr(a, "maximum")
            if kind == "finite_or_nan" and "if" in e and e["if"] not in self.inputs:
                fail("%s: the mask %r of a finite_or_nan claim is not an input" % (where, e["if"]))
            if kind == "finite_or_nan" and "steps" in e and (not isinstance(e["steps"], int) or e["steps"] < 1):
                fail("%s: the steps %r of a finite_or_nan claim are not an integer >= 1" % (where, e["steps"]))
            own = kind in ("holds", "maximum") or (kind == "upper" and "value" in e)
            if kind not in OWN_SET_KINDS and not own and self.value is None:
                fail("%s: a %s claim needs a value, and the kernel has none" % (where, kind))
            if e.get("zero_factor") not in (None, True) or e.get("bounded_exactly") not in (None, True):
                fail("%s: zero_factor and bounded_exactly are true, or left out" % where)
            if e.get("smallest_radius") not in (None, True):
                fail("%s: smallest_radius is true, or left out" % where)
            if kind in ("certain", "trit"):
                self.check_set_predicate(e, where)
            if kind == "ball_set" and e["set"] not in KNOWN_SET_OPERATIONS:
                fail("%s: the set operation %r of a ball_set claim has no template" % (where, e["set"]))
            if kind == "interval_set" and e["set"] not in KNOWN_SET_OPERATIONS:
                fail("%s: the set operation %r of an interval_set claim has no template" % (where, e["set"]))
            if kind == "ball_of_interval" and e["special"] not in KNOWN_BALL_SPECIALS:
                fail("%s: the special values %r of a ball_of_interval claim have no template" % (where, e["special"]))
            if e.get("zero_factor"):
                # The value of a product, or for an interval kernel its set (stage B1, interval_mul_2).
                product = (parse(e["set"], "%s, set" % where, set(e["intervals"])) if kind == "encloses_interval"
                           else self.value)
                if not self.extended or product[0] != "*":
                    fail("%s: zero_factor is about a product, in the extended domain" % where)
            tight = e.get("tight")
            if tight is not None and (tight.get("kind") not in KNOWN_TIGHT
                                      or set(tight) - {"kind"} - KNOWN_TIGHT[tight["kind"]]):
                fail("%s: the tightness %r has no template" % (where, tight))
            if kind == "outward" or (tight or {}).get("kind") == "outward":
                for key in ("rel", "abs"):
                    for fmt in self.formats():
                        claim_constant((tight or e)[key], "%s, %s" % (where, key), fmt, KERNEL_CLAIMS)
                conds = e.get("exact_when") if kind == "outward" else None
                for c in conds or [x for side in (tight or {}).get("exact_when", {}).values() for x in side]:
                    if set(c) != {"zero"}:
                        fail("%s: the condition %r of an outward claim has no template" % (where, c))
            for c in e.get("bounded_when", []):
                if set(c) not in ({"abs_le", "omega"}, {"abs_le", "exp"}) or c["abs_le"] != e["set"]:
                    fail("%s: the bounded_when condition %r has no template" % (where, c))
            for c in e.get("midpoint_when", []):
                if set(c) != {"half_in_format"} or c["half_in_format"] not in self.inputs:
                    fail("%s: the midpoint_when condition %r has no template" % (where, c))
        # Whether the kernel has a statement on finite operands (the real model) is what the claims
        # say with ieee_only, and nothing else (architecture.md, "Claims of the non-finite layer").
        if "ieee_only" in entry and entry["ieee_only"] is not True:
            fail("%s: ieee_only is %r; the claims give it as true or leave it out" % (where, entry["ieee_only"]))
        self.ieee_only = entry.get("ieee_only", False)
        if self.ieee_only and not self.extended:
            fail("%s: ieee_only is true, but the domain is %r, not extended" % (where, self.domain))
        if self.ieee_only and entry["status"] != entry["ieee_status"]:
            fail("%s: a kernel with only an IEEE-model statement (ieee_only) has the status %r and the "
                 "ieee_status %r, which architecture.md says are one" % (where, entry["status"], entry["ieee_status"]))
        kinds = [e["kind"] for e in entry["ensures"]]
        only_ieee = [k for k in kinds if k in IEEE_ONLY_KINDS] + (["represents"] if kinds == ["represents"] else [])
        if only_ieee and not self.ieee_only:
            fail("%s: the claim kind %s exists only for a kernel without a statement on finite operands, and the "
                 "kernel is not ieee_only" % (where, only_ieee[0]))
        self.finite_reading = not self.ieee_only
        # The entries of the statement on finite operands: represents adds nothing there to the
        # others (an exact error and normalized), and says which canonical value comes out in the
        # extended domain.
        self.finite_entries = [e for e in entry["ensures"] if e["kind"] != "represents"] if self.finite_reading else []
        self.errors = [e for e in entry["ensures"] if e["kind"] == "error"]
        for fmt, _, _, _ in FORMATS:
            if len(entry["instances"].get(fmt, [])) != len(self.errors):
                fail("%s: %s has %d constants for %d error claims"
                     % (where, fmt, len(entry["instances"].get(fmt, [])), len(self.errors)))

    @staticmethod
    def formats():
        """(p, q_min) of each format of FORMATS: q_min + q_max = 3 - 2p."""
        return [(p, 3 - 2 * p - qmax) for _, _, p, qmax in FORMATS]

    def limbs(self, name):
        return self.listing["limbs"][name]

    def lead_limb(self, name):
        return self.limbs(name)[0]

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

    def expr(self, text, where, names=None, constants=False):
        return parse(text, "kernel %s, %s" % (self.name, where), names or self.names, constants)

    def ball_names(self):
        """{(center, radius): ball name} of the encloses claims, to name the balls of requirements."""
        out = {}
        for e in self.entry["ensures"]:
            if e["kind"] in ("encloses", "ball_set") or (e["kind"] in ("certain", "trit") and "balls" in e):
                for b, cr in e["balls"].items():
                    out[(cr["center"], cr["radius"])] = b
        return out

    def is_two_limbs(self, name, what):
        if len(self.limbs(name)) != 2:
            fail("kernel %s: %s on %d limbs has no template" % (self.name, what, len(self.limbs(name))))

    def normalized_text(self, x, pair=None):
        self.is_two_limbs(x, "normalized(%s)" % x)
        l0, l1 = (name_tex(l) for l in self.limbs(x))
        return "$%s$ is normalized: $%s = \\mathrm{RN}(%s + %s)$" % (pair or name_tex(x), l0, l0, l1)

    def canonical_text(self, x):
        self.is_two_limbs(x, "canonical(%s)" % x)
        return ("$%s$ is canonical: finite and normalized, or $(\\pm\\infty, \\pm 0)$, or "
                "$(\\mathrm{NaN}, \\mathrm{NaN})$" % name_tex(x))

    # Requirements, in each reading. On finite operands a requirement may say several things.
    def finite_requirement(self, kind, args):
        if kind in ("normalized", "canonical"):       # canonical is normalized on finite operands
            return [self.normalized_text(args[0])]
        if kind == "ball":                            # a finite ball: its center and its radius
            c, r = args
            center = (self.normalized_text(c) if len(self.limbs(c)) == 2
                      else "$%s$ is a number of `T`" % name_tex(c))
            return [center, "$%s \\ge 0$" % name_tex(r)]
        if kind == "abs_ge":
            return ["$\\lvert %s\\rvert \\ge \\lvert %s\\rvert$" % (name_tex(args[0]), name_tex(args[1]))]
        if kind == "nonneg":
            return ["$%s \\ge 0$" % name_tex(args[0])]
        if kind == "power_of_two":
            c = name_tex(args[0])
            return ["$%s$ is a power of two: $%s = 2^n$ for an integer $n$" % (c, c)]
        if kind == "count":
            m = name_tex(args[0])
            return ["$%s = 0$ or $%s \\ge 1$, as a number of terms is" % (m, m)]
        if kind == "format":
            return ["The format contains $\\tfrac12$: $\\eta \\le \\tfrac12$, as `float` and `double` do"]
        if kind == "at_most":
            return ["$%s \\le %s$" % (name_tex(args[0]), args[1])]
        if kind == "not_nan":                         # a finite operand is not a NaN
            return []
        fail("kernel %s: the requirement %s has no reading on finite operands" % (self.name, kind))

    def extended_requirement(self, kind, args):
        if kind == "canonical":
            return self.canonical_text(args[0])
        if kind == "ball":
            c, r = args
            b = self.ball_names().get((c, r))
            ball = "$%s$, of center $%s$ and radius $%s$," % (name_tex(b).upper(), name_tex(c), name_tex(r)) \
                if b else "the ball of center $%s$ and radius $%s$" % (name_tex(c), name_tex(r))
            return ("%s is a canonical ball: a finite ball (finite center%s, finite radius $\\ge 0$), the "
                    "whole line (center 0, radius $+\\infty$), or the empty set (every limb a NaN)" % (
                        ball, ", normalized" if len(self.limbs(c)) == 2 else ""))
        if kind == "nonneg":
            return "$%s \\ge 0$, or $+\\infty$, or a NaN" % name_tex(args[0])
        if kind == "power_of_two":
            c = name_tex(args[0])
            return "$%s$ is a finite power of two: $%s = 2^n$ for an integer $n$" % (c, c)
        if kind == "interval":
            lo, hi = args
            name = self.interval_names().get((lo, hi))
            what = "$%s = [%s, %s]$" % (name_tex(name).upper(), name_tex(lo), name_tex(hi)) if name else \
                "$[%s, %s]$" % (name_tex(lo), name_tex(hi))
            two = len(self.limbs(lo)) == 2
            return ("%s is a canonical interval: the empty set, $%s = +\\infty$ and $%s = -\\infty$%s, or a nonempty "
                    "interval, neither bound a NaN, $%s \\le %s$, $%s < +\\infty$, $%s > -\\infty$, each bound %s; its "
                    "members are the real numbers between its bounds" % (
                        what, name_tex(lo), name_tex(hi), " (each followed by a zero)" if two else "",
                        name_tex(lo), name_tex(hi), name_tex(lo), name_tex(hi),
                        "finite and normalized or $(\\pm\\infty, \\pm 0)$" if two else "a number of `T` or an infinity"))
        if kind == "not_nan":
            if len(self.limbs(args[0])) == 2:          # stage B1: a canonical value that is not a NaN
                return "$%s$ is not a NaN: a finite normalized pair or $(\\pm\\infty, \\pm 0)$" % name_tex(args[0])
            return "$%s$ is a number of `T` or an infinity, not a NaN" % name_tex(args[0])
        fail("kernel %s: the requirement %s has no reading in the extended domain" % (self.name, kind))

    def interval_names(self):
        """{(lower, upper): interval name} of the encloses_interval claims."""
        out = {}
        for e in self.entry["ensures"]:
            if e["kind"] in ("encloses_interval", "interval_set") or (e["kind"] in ("certain", "trit") and
                                                                     "intervals" in e):
                for n, b in e["intervals"].items():
                    out[(b["lower"], b["upper"])] = n
        return out

    def extended_free_inputs(self):
        """The inputs no requirement constrains: in the extended domain, any value of T (for several
        limbs, every limb: the finish of a fold takes any state)."""
        covered = {a for _, args in self.requires for a in args}
        return [i for i in self.inputs if i not in covered]

    # Claims, in the finite reading.
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
        elif e["form"] == "T":      # the magnitudes of the terms of the value
            rho = "(%s)" % " + ".join("\\lvert %s\\rvert" % tex(t) for t in sum_terms(self.value))
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

    def exact_tex(self, conds):
        """The conditions of an exact_when as text: EXPR, over the inputs and their limbs NAME[I],
        is zero or above (at least) K, an expression over u and eta."""
        if not conds:
            fail("kernel %s: an exact_when with no condition" % self.name)
        limbs = {l for i in self.inputs for l in self.limbs(i)}
        parts = []
        for c in conds:
            if set(c) == {"zero"}:
                # zero(EXPR), of outward (Milestone 2): EXPR = 0.
                parts.append("$%s = 0$" % tex(parse(c["zero"], "kernel %s, exact_when" % self.name,
                                                    set(self.inputs))))
                continue
            if set(c) == {"mask"}:
                # mask(NAME), of upper (the radius of the scaling of a BallVector): a mask input is true.
                if c["mask"] not in self.inputs:
                    fail("kernel %s: the exact_when condition %r names no input" % (self.name, c))
                parts.append("$%s$ is true" % name_tex(c["mask"]))
                continue
            if set(c) == {"abs_le", "omega"} and c["omega"] is True:
                # abs_le(EXPR,omega), of certain and trit: |EXPR| <= Omega.
                parts.append("$\\lvert %s\\rvert \\le \\Omega$" % tex(parse(
                    c["abs_le"], "kernel %s, exact_when" % self.name, set(self.inputs))))
                continue
            kinds = [x for x in KNOWN_EXACT_CONDITIONS if x in c]
            if len(kinds) != 1 or set(c) != {kinds[0], "than"}:
                fail("kernel %s: the exact_when condition %r is not one this script knows" % (self.name, c))
            text = c[kinds[0]]

            def limb(m):
                name, i = m.group(1), int(m.group(2))
                if name not in self.inputs or i >= len(self.limbs(name)):
                    fail("kernel %s: the exact_when condition %r names a limb %s[%d] that is not one" % (
                        self.name, c, name, i))
                return self.limbs(name)[i]
            node = parse(re.sub(r"([a-z][a-z0-9]*)\[(\d+)\]", limb, text), "kernel %s, exact_when" % self.name,
                         set(self.inputs) | limbs)
            bound = parse(c["than"], "kernel %s, exact_when" % self.name, {"u", "eta"})
            x = tex(node)
            parts.append("$%s = 0$ or $\\lvert %s\\rvert %s %s$" % (x, x, KNOWN_EXACT_CONDITIONS[kinds[0]], tex(bound)))
        return ", ".join(parts[:-1]) + (", and " if len(parts) > 2 else " and ") + parts[-1] if len(parts) > 1 \
            else parts[0]

    def check_set_predicate(self, e, where):
        """The relation, the arguments and the sets of a certain or trit claim are ones the pages
        have words for: intervals or balls (one of them), each named by an argument."""
        rel, args = e["rel"], e["args"]
        known = KNOWN_TRIT_RELATIONS if e["kind"] == "trit" else set(KNOWN_SET_RELATIONS)
        if rel not in known or len(args) != KNOWN_SET_RELATIONS[rel]:
            fail("%s: the relation %r of a %s claim has no template" % (where, rel, e["kind"]))
        if ("intervals" in e) == ("balls" in e):
            fail("%s: a %s claim names intervals or balls, one of them" % (where, e["kind"]))
        sets = e.get("intervals", e.get("balls"))
        if e.get("exact") not in (None, True) or ("exact" in e and "exact_when" in e):
            fail("%s: exact is true or left out, and not with exact_when" % where)
        for a in args[1:] if rel == "member" else args:
            if a not in sets and not (rel in ("lt", "le", "eq") and a == "0"):
                fail("%s: the argument %r of a %s claim is not one of its sets" % (where, a, e["kind"]))
        if rel == "member" and args[0] not in self.inputs:
            fail("%s: the point %r of a member claim is not an input" % (where, args[0]))
        for b in sets.values():
            for v in b.values():
                if v not in self.inputs:
                    fail("%s: %r of a set of a %s claim is not an input" % (where, v, e["kind"]))

    def limb_expr(self, text, what):
        """An expression over the inputs and their limbs NAME[I] (a maximum claim), as a tree, each
        limb by its name."""
        limbs = {l for i in self.inputs for l in self.limbs(i)}

        def limb(m):
            name, i = m.group(1), int(m.group(2))
            if name not in self.inputs or i >= len(self.limbs(name)):
                fail("kernel %s: the %s claim names a limb %s[%d] that is not one" % (self.name, what, name, i))
            return self.limbs(name)[i]
        return parse(re.sub(r"([a-z][a-z0-9]*)\[(\d+)\]", limb, text), "kernel %s, %s" % (self.name, what),
                     set(self.inputs) | limbs)

    def when_tex(self, e):
        if e.get("when") not in KNOWN_WHEN:
            fail("kernel %s: the condition when=%r has no template" % (self.name, e["when"]))
        if e.get("when") == "product_large":
            v = tex(self.value)
            # 2^(2p-1) eta, written without p, which a kernel may use as a name (two_prod's product).
            return "when $%s = 0$ or $\\lvert %s\\rvert \\ge \\eta/(2u^2)$" % (v, v)
        return None

    def encloses_text(self, e):
        balls = e["balls"]
        names = set(balls) | set(self.inputs)
        for b, cr in balls.items():
            if set(cr) != {"center", "radius"} or cr["center"] not in self.inputs or cr["radius"] not in self.inputs:
                fail("kernel %s: the ball %r of an encloses claim is not a center and a radius of the inputs"
                     % (self.name, b))
        s = self.expr(e["set"], "encloses", names)
        if not balls:
            # The operands are points (Milestone 2, add_ball_2_2): the radius bounds the error.
            return "$\\lvert %s - %s\\rvert \\le %s$: $%s$ bounds the error of $%s$" % (
                parenthesized(s), self.out_tex(e["center"]), name_tex(e["radius"]), name_tex(e["radius"]),
                self.out_tex(e["center"]))
        over = ", ".join("$\\lvert %s - %s\\rvert \\le %s$" % (name_tex(b), name_tex(cr["center"]),
                                                                name_tex(cr["radius"]))
                         for b, cr in balls.items())
        return "$\\lvert %s - %s\\rvert \\le %s$ for all real %s with %s" % (
            parenthesized(s), name_tex(e["center"]), name_tex(e["radius"]),
            " and ".join("$%s$" % name_tex(b) for b in balls), over)

    def finite_bullet(self, e, short=False):
        kind = e["kind"]
        if kind == "normalized":
            of = e["of"]
            self.is_two_limbs(of, "normalized(%s)" % of)
            limbs = self.limbs(of)
            pair = "(%s, %s)" % (name_tex(limbs[0]), name_tex(limbs[1])) if self.expanded(of) else name_tex(of)
            if short:
                return "$%s$ normalized" % pair
            return self.normalized_text(of, pair)
        if kind == "error":
            of, v = self.out_tex(e["of"]), tex(self.value)
            bound = self.bound_tex(e)
            when = self.when_tex(e)
            if bound is None:
                text = "$%s = %s$ exactly" % (of, v)
            else:
                left = "%s - %s" % (of, tex(self.value, 1, right=True))
                text = "$\\lvert %s\\rvert \\le %s$" % (left, bound)
            text += (", " + when if when else "")
            if "exact_when" in e and not short:
                text += "; and $%s = %s$ exactly when %s" % (of, v, self.exact_tex(e["exact_when"]))
            if "exact_flag" in e and not short:
                text += "; $%s$ is true exactly when %s" % (name_tex(e["exact_flag"]), self.exact_tex(e["exact_when"]))
            return text
        if kind == "leading_rounded":
            return "$%s = \\mathrm{RN}(%s)$" % (name_tex(self.lead_limb(e["of"])), tex(self.value))
        if kind == "rounded":
            if e["mode"] not in KNOWN_MODES:
                fail("kernel %s: the rounding mode %r has no template" % (self.name, e["mode"]))
            # A value of its own (the accumulator's sum of magnitudes), or the kernel's.
            v = self.limb_expr(e["value"], "rounded") if "value" in e else self.value
            text = "$%s = \\mathrm{%s}(%s)$" % (name_tex(e["of"]), KNOWN_MODES[e["mode"]], tex(v))
            when = self.when_tex(e)
            if short:
                return text + (" " + when if when else "")
            return text + {
                "nearest": ": the number of the format nearest to $%s$, ties to even",
                "down": ": the largest number of the format not above $%s$",
                "up": ": the smallest number of the format not below $%s$",
            }[e["mode"]] % tex(v) + (", " + when if when else "")
        if kind == "neighbor":
            r, v = name_tex(e["of"]), tex(self.value)
            step, where = KNOWN_SIDES[kind][e["side"]]
            text = "$%s = \\mathrm{%s}(%s)$" % (r, step, v)
            return text if short else text + ": the next number of the format %s $%s$" % (where, v)
        if kind == "bound":
            r, v, n = name_tex(e["of"]), tex(self.value), e["steps"]
            rounding, direction = KNOWN_SIDES[kind][e["side"]]
            below = e["side"] == "below"
            side = "$%s \\le %s$" % (r, v) if below else "$%s \\ge %s$" % (r, v)
            if short:
                return "%s, at most %d step%s %s $\\mathrm{%s}(%s)$" % (
                    side, n, "" if n == 1 else "s", "below" if below else "above", rounding, v)
            return ("%s, and $%s$ is $\\mathrm{%s}(%s)$ or at most %d step%s of the format %s it: a bound on that "
                    "side of the exact value, at most %d number%s of the format beyond its rounding %s" % (
                        side, r, rounding, v, n, "" if n == 1 else "s", "below" if below else "above", n,
                        "" if n == 1 else "s", direction))
        if kind == "upper" and "value" in e:
            # An exported bound: its own value, under its mask, and no closeness claimed.
            r, v = name_tex(e["of"]), tex(self.expr(e["value"], "upper value", self.names | {"u", "eta"},
                                                    constants=True))
            text = "$%s \\ge %s$" % (r, v)
            if "gaps" in e:
                text += ", at most $%s$ gaps above" % num_tex(fractions.Fraction(e["gaps"]))
            if "if" in e:
                text = ("when $%s$ is true, " % name_tex(e["if"])) + text
            if "unless" in e:
                text = ("when $%s$ is false, " % name_tex(e["unless"])) + text
            if "exact_when" in e and not short:
                text += "; and $%s = %s$ exactly when %s" % (r, v, self.exact_tex(e["exact_when"]))
            return text
        if kind == "holds":
            a, b = (tex(self.expr(x, "holds", self.names | {"u", "eta"}, constants=True)) for x in e["args"])
            return "when $%s$ is true, $%s %s %s$" % (name_tex(e["if"]), a, KNOWN_RELS[e["rel"]], b)
        if kind == "maximum":
            a, b = (tex(self.limb_expr(x, "maximum")) for x in e["args"])
            if short:
                return "$%s = \\max(%s, %s)$" % (name_tex(e["of"]), a, b)
            return "$%s = \\max(%s, %s)$, exactly: the larger of the two" % (name_tex(e["of"]), a, b)
        if kind == "upper":
            r, v = name_tex(e["of"]), tex(self.value)
            gaps = num_tex(fractions.Fraction(e["gaps"]))
            if short:
                return "$%s \\ge %s$, at most $%s$ gaps above" % (r, v, gaps)
            return ("$%s \\ge %s$, and $%s - (%s) \\le %s\\,(%s - \\mathrm{pred}(%s))$: at most %s gaps "
                    "of the format above the exact value" % (r, v, r, v, gaps, r, r, "$%s$" % gaps))
        if kind == "predicate":
            rel = self.relation(e)
            if short:
                return "exactly whether $%s$" % rel
            return "$%s$ is true exactly when $%s$, for the exact values" % (name_tex(e["of"]), rel)
        if kind == "outward":
            o, v = self.out_tex(e["of"]), tex(self.value)
            below = e["side"] == "below"
            side = "$%s \\le %s$" % (o, v) if below else "$%s \\ge %s$" % (o, v)
            if short:
                return "%s, within $A\\lvert %s\\rvert + B$%s" % (side, v, ", exact when zero" if "exact_when" in e else "")
            text = ("%s, and $\\lvert %s - (%s)\\rvert \\le A\\,\\lvert %s\\rvert + B$: a %s bound, moved outward from "
                    "the result rounded to nearest by a bound of its error, with the constants $A$ and $B$ below" % (
                        side, o, v, v, "lower" if below else "upper"))
            if "exact_when" in e:
                text += "; and $%s = %s$ exactly when %s" % (o, v, self.exact_tex(e["exact_when"]))
            return text
        if kind == "encloses":
            s = tex(self.expr(e["set"], "encloses", set(e["balls"]) | set(self.inputs)))
            if short and not e["balls"]:
                return "$\\lvert %s - %s\\rvert \\le %s$" % (parenthesized(self.expr(e["set"], "encloses")),
                                                           self.out_tex(e["center"]), name_tex(e["radius"]))
            if short:
                return "contains every $%s$%s" % (s, ", exactly when nothing underflows" if "exact_when" in e else "")
            text = self.encloses_text(e)
            if "exact_when" in e:
                text += ("; and when %s, the ball is exactly the set: every number within $%s$ of $%s$ is a $%s$ "
                         "of that kind, so that $%s \\mp %s$ are the least and the greatest $%s$" % (
                             self.exact_tex(e["exact_when"]), name_tex(e["radius"]), name_tex(e["center"]), s,
                             name_tex(e["center"]), name_tex(e["radius"]), s))
            return text
        fail("kernel %s: the claim kind %r has no reading on finite operands" % (self.name, kind))

    def relation(self, e):
        if e["rel"] not in KNOWN_RELS or len(e["args"]) != 2:
            fail("kernel %s: the predicate %r has no template" % (self.name, e["rel"]))
        a, b = (tex(self.expr(x, "predicate")) for x in e["args"])
        return "%s %s %s" % (a, KNOWN_RELS[e["rel"]], b)

    def finite_short(self):
        entries = self.finite_entries
        parts = [self.finite_bullet(e, short=True) for e in entries
                 if e["kind"] != "normalized" and not (e["kind"] in ("error", "rounded") and e.get("when"))]
        normalized = [e for e in entries if e["kind"] == "normalized"]
        if normalized and parts:
            parts[-1] += ", normalized"
        return "; ".join(parts) or "; ".join(self.finite_bullet(e, short=True) for e in entries)

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
        """The oracle's label of an ensures entry, as the brute-force summaries print it, for the
        kinds of LABELLED_KINDS (oracle/kairn_oracle/claims.py, Entry._label; bvec.py,
        label_suffix and label; intervals.py and enclosure.py, label); for another kind, its kind
        and outputs only, which the oracle's label starts with."""
        return entry_label(e)


def renamed_core(core, full):
    """The core of a full kernel, with the full kernel's output names: the outputs correspond by
    position (architecture.md, "Claims of the non-finite layer")."""
    if core.inputs != full.inputs:
        fail("kernel %s: its core %s has the inputs %s, not %s" % (full.name, core.name, core.inputs, full.inputs))
    if [o["limbs"] for o in core.entry["outputs"]] != [o["limbs"] for o in full.entry["outputs"]]:
        fail("kernel %s: its core %s has outputs of another shape" % (full.name, core.name))
    mapping = dict(zip(core.outputs, full.outputs))
    entry = json.loads(json.dumps(core.entry))
    entry["outputs"] = json.loads(json.dumps(full.entry["outputs"]))
    for e in entry["ensures"]:
        for f in ("of", "center", "radius"):
            if f in e:
                e[f] = mapping.get(e[f], e[f])
    limbs = {n: l for n, l in core.listing["limbs"].items() if n not in mapping}
    for c_out, f_out in mapping.items():
        limbs[f_out] = full.listing["limbs"][f_out]
    listing = dict(core.listing, limbs=limbs)
    return Kernel(entry, listing)


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
        power = "1" if b == 0 else "2^{%d}" % b
        if rest and rest & (rest - 1) == 0:
            a = rest.bit_length() - 1
            return "\\frac{%d}{2^{%d} + %s}" % (n, a, power)
        if (d + low) & (d + low - 1) == 0:
            a = (d + low).bit_length() - 1
            return "\\frac{%d}{2^{%d} - %s}" % (n, a, power)
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


def power_tex(e):
    return "2^{e_{\\max}}" if e == 0 else "2^{e_{\\max} %s %d}" % ("+" if e > 0 else "-", abs(e))


# --- Brute-force results --------------------------------------------------------------------------

# The kinds whose oracle label entry_label prints, from the fields of the claims alone. The labels of
# the others (ball_of_interval, encloses_interval, interval_of_ball, makes_ball from an interval,
# neighbor) carry what the oracle derives from them, such as the text of its constants; for those
# entry_label prints the kind and the outputs, which the oracle's label starts with.
LABELLED_KINDS = {"error", "normalized", "leading_rounded", "represents", "rounded", "upper", "holds",
                  "maximum", "predicate", "encloses", "outward", "extends", "finite_or_nan", "bound",
                  "certain", "trit", "set_bound", "interval_set", "ball_set", "splits", "ball_splits",
                  "makes_interval", "makes_ball"}


def _of(e):
    of = e.get("of", "")
    return "+".join(of) if isinstance(of, list) else of


def _finite_when_text(fw):
    """oracle/kairn_oracle/claims.py, _fw_text."""
    if not fw:
        return "nothing (no condition claimed)"
    return " and ".join("|%s| <= 2^(qmax+p%+d)" % (c["abs_le"], c["exp"]) if c.get("exp") else
                        "|%s| <= 2^(qmax+p)" % c["abs_le"] for c in fw)


def _condition_text(c):
    """A condition of exact_when: oracle/kairn_oracle/intervals.py, condition_text."""
    if "zero" in c:
        return "%s = 0" % c["zero"]
    op = "zero_or_abs_gt" if "zero_or_abs_gt" in c else "zero_or_abs_ge"
    return "%s = 0 or |%s| %s %s" % (c[op], c[op], ">" if op == "zero_or_abs_gt" else ">=", c["than"])


def _exact_when_text(ew):
    return " and ".join("(%s)" % _condition_text(c) for c in ew)


def _suffix(e):
    """What the fields of the ball vectors add to an entry: oracle/kairn_oracle/bvec.py, label_suffix."""
    s = ""
    if e.get("exact_flag"):
        s += ", exact_flag %s" % e["exact_flag"]
    if e.get("nonneg"):
        s += ", not below zero"
    if e.get("if_all"):
        s += " if all of %s" % ", ".join(e["if_all"])
    if e["kind"] == "rounded" and "value" in e:
        s += " of %s" % e["value"].strip()
    return s


def _sets_text(e):
    if "intervals" in e:
        return ", ".join("%s=[%s, %s]" % (n, s["lower"], s["upper"]) for n, s in e["intervals"].items())
    return ", ".join("%s=[%s +- %s]" % (n, s["center"], s["radius"]) for n, s in e["balls"].items())


def entry_label(e):
    """The oracle's label of a claim (see Kernel.label)."""
    kind, of = e["kind"], _of(e)
    if kind == "error":
        s = "error(%s) form %s, c=%s, k=%s, t=%s" % (of, e["form"], e["c"], e["k"], e["t"])
        if e.get("when"):
            s += ", when %s" % e["when"]
        if "exact_when" in e:
            s += ", exact when %s" % _exact_when_text(e["exact_when"])
        return s + _suffix(e)
    if kind in ("normalized", "leading_rounded", "represents"):
        return "%s(%s)" % (kind, of)
    # A zero factor (the interval kernels): oracle/kairn_oracle/intervals.py, read_zero_factor.
    zero = ", a zero factor gives zero" if e.get("zero_factor") else ""
    if kind == "rounded":
        if e.get("when"):
            return "rounded(%s) %s, when %s" % (of, e["mode"], e["when"]) + zero
        return "rounded(%s) %s" % (of, e["mode"]) + _suffix(e) + zero
    if kind == "upper" and "if" in e:
        return "upper(%s) >= %s if %s" % (of, str(e["value"]).strip(), e["if"])
    if kind == "upper" and "value" in e:
        s = "upper(%s) >= %s" % (of, str(e["value"]).strip())
        if "unless" in e:
            s += " unless %s" % e["unless"]
        if "exact_when" in e:
            s += ", exactly when %s" % " and ".join(
                "%s true" % c["mask"] if "mask" in c else "(%s)" % _condition_text(c) for c in e["exact_when"])
        return s
    if kind == "upper":
        return "upper(%s) gaps=%s" % (of, e["gaps"])
    if kind == "holds":
        return "holds %s(%s, %s) if %s" % (e["rel"], e["args"][0].strip(), e["args"][1].strip(), e["if"])
    if kind == "maximum":
        return "maximum(%s) of %s, %s" % (of, e["args"][0].strip(), e["args"][1].strip())
    if kind == "predicate":
        return "predicate(%s) %s(%s)" % (of, e["rel"], ", ".join(e["args"]))
    if kind == "encloses":
        s = "encloses(%s, %s) %s over %s" % (e["center"], e["radius"], e["set"].strip(), _sets_text(e))
        if "finite_when" in e:
            s += ", B1-B4, finite when %s" % _finite_when_text(e["finite_when"])
        if "exact_when" in e:
            s += ", exactly the set when %s" % _exact_when_text(e["exact_when"])
        return s
    if kind == "outward":
        s = "outward(%s) %s" % (of, e["side"])
        if e.get("exact_when"):
            s += ", exact when %s" % _exact_when_text(e["exact_when"])
        return s + zero
    if kind == "extends":
        return "extends(%s) F1-F5, core %s, lead %s, finite when %s" % (
            of, e["core"], e["lead"], _finite_when_text(e.get("finite_when", [])))
    if kind == "finite_or_nan":
        s = "finite_or_nan(%s) flag %s" % (of, e["flag"])
        if "if" in e:
            s += " if %s" % e["if"]
        if e.get("steps"):
            s += ", stepped up %d" % e["steps"]
        return s + _suffix(e)
    if kind == "bound":
        return "bound(%s) %s, steps=%d" % (of, e["side"], e["steps"]) + zero
    if kind in ("certain", "trit"):
        out = of if kind == "certain" else "yes %s, no %s" % (e["yes"], e["no"])
        s = "%s(%s) %s(%s) over %s" % (kind, out, e["rel"], ", ".join(e["args"]), _sets_text(e))
        if e.get("exact"):
            s += ", exact"
        if e.get("exact_when"):
            s += ", exact when %s" % " and ".join("|%s| <= Omega" % c["abs_le"] for c in e["exact_when"])
        return s
    if kind == "set_bound":
        s = "set_bound(%s) %s %s over %s" % (of, e["side"], e["set"].strip(), _sets_text(e))
        if e.get("tight"):
            s += ", tight rounded" + (", steps %d" % e["tight"]["steps"] if e["tight"].get("steps") else "")
        return s
    if kind == "interval_set":
        return "interval_set(%s, %s) %s of %s" % (e["lower"], e["upper"], e["set"], _sets_text(e))
    if kind == "ball_set":
        return "ball_set(%s, %s) %s of %s" % (e["center"], e["radius"], e["set"], _sets_text(e))
    if kind == "splits":
        a, b = e["parts"]
        return "splits [%s, %s], [%s, %s] of [%s, %s]" % (a["lower"], a["upper"], b["lower"], b["upper"],
                                                          e["from"]["lower"], e["from"]["upper"])
    if kind == "ball_splits":
        a, b = e["parts"]
        return "ball_splits [%s +- %s], [%s +- %s] of [%s +- %s]" % (
            a["center"], a["radius"], b["center"], b["radius"], e["from"]["center"], e["from"]["radius"])
    if kind == "makes_interval":
        return "makes_interval(%s, %s) from lower %s, upper %s" % (
            e["lower"], e["upper"], e["from"]["lower"], e["from"]["upper"])
    if kind == "makes_ball" and "center" in e["from"]:
        return "makes_ball(%s, %s) from center %s, radius %s" % (
            e["center"], e["radius"], e["from"]["center"], e["from"]["radius"])
    outputs = of or ", ".join(e[f] for f in ("center", "radius", "lower", "upper") if f in e)
    return "%s(%s)" % (kind, outputs)


def labelled(e):
    """Whether entry_label prints the oracle's whole label of e."""
    return e["kind"] in LABELLED_KINDS and not (e["kind"] == "makes_ball" and "center" not in e["from"])


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


def judged_by(doc, name):
    """Whether a stored summary judged a kernel: its compiled runs or the interpreter's."""
    return name in doc["compiled"]["kernels"] or any(r["kernel"] == name for r in doc["interp"]["enumerations"])


def short_commits(docs):
    return sorted({c[:7] for d in docs for c in d.get("commit", [])})


def brute_of(name, campaign, docs, same_claims):
    """What the summaries docs of one campaign say about one kernel, merged over machines and
    runners; then the rows of its supplementary runs, apart. docs are the summaries of the campaign
    whose runs count for the kernel; same_claims(doc) says whether a summary judged the claims the
    kernel has now. When some did and some did not, the rows of those that did not are apart too,
    marked "other claims"."""
    docs = [d for d in docs if judged_by(d, name)]
    mixed = len({same_claims(d) for d in docs}) > 1
    rows, findings, extended = [], [], False
    for part, suffix in (("main", ""), ("supplementary", ", supplementary run")):
        for same in (True, False):
            group = [d for d in docs if d["_part"] == part and same_claims(d) == same]
            b = brute_rows(name, group, suffix + (", other claims" if mixed and not same else "")) if group else None
            if b is None:
                continue
            for r in b["rows"]:
                r["supplementary"] = part == "supplementary"
                r["same_claims"] = same
            rows += b["rows"]
            findings += b["findings"]
            extended = extended or b["extended"]
    if not rows and not findings:
        return None
    return {"rows": rows, "findings": findings, "extended": extended,
            "main": short_commits(d for d in docs if d["_part"] == "main"),
            "supplementary": short_commits(d for d in docs if d["_part"] == "supplementary"),
            "same": short_commits(d for d in docs if same_claims(d)),
            "other": short_commits(d for d in docs if not same_claims(d))}


def brute_rows(name, docs, suffix):
    rows, findings = [], []
    for fmt, ctype, _, _ in FORMATS:
        row = None
        for d in docs:
            s = d["compiled"]["kernels"].get(name, {}).get(fmt)
            if not s:
                continue
            if row is None:
                row = {"title": "`%s` (`%s`), compiled%s" % (fmt, ctype, suffix), "machines": 0, "runners": 0,
                       "cases": 0, "judged": 0, "failed": 0, "invalid": 0, "entries": None, "ok": True,
                       "key": fmt}
            row["machines"] += 1
            row["runners"] += len(s["runners"])
            for key in ("cases", "judged", "failed", "invalid"):
                row[key] += s["counts"].get(key, 0)
            row["entries"] = merge(row["entries"], s["entries"], fmt)
            row["ok"] = row["ok"] and s.get("guards") == "ok"
        if row:
            rows.append(row)
    interp = None
    for d in docs:
        for r in d["interp"]["enumerations"]:
            if r["kernel"] != name:
                continue
            if interp is None:
                interp = {"title": "toy formats, every operand" + suffix, "domains": 0, "complete": 0, "formats": [],
                          "cases": 0, "judged": 0, "failed": 0, "invalid": 0, "entries": None, "ok": True,
                          "key": "toy", "enumerations": []}
            interp["domains"] += 1
            interp["complete"] += 1 if r.get("complete") else 0
            # A domain is the format, the restriction of the operands and the domain of the claims:
            # two enumerations of one domain, of one code, are of the same operands.
            counts = r.get("counts", {})
            interp["enumerations"].append({
                "domain": (r["format"], json.dumps(r.get("restrict", []), sort_keys=True), r.get("domain")),
                "complete": bool(r.get("complete")), "judged": counts.get("judged", 0),
                "failed": counts.get("failed", 0) + counts.get("invalid", 0), "ok": r.get("guards") == "ok"})
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
    # Whether the runs judged the kernel in the extended domain (the oracle's judge of the
    # non-finite layer, on every operand): the summaries say so per series since they record a
    # domain; older ones do not, and judged the statement on finite operands only.
    extended = any(s.get("domain") == "extended"
                   for d in docs for fmts in [d["compiled"]["kernels"].get(name, {})]
                   for s in fmts.values()) or any(
        r.get("domain") == "extended" for d in docs for r in d["interp"]["enumerations"]
        if r["kernel"] == name)
    return {"rows": rows, "findings": findings, "extended": extended} if rows or findings else None


# --- Pages ----------------------------------------------------------------------------------------

def operand_types(f):
    return ", ".join("`%s`" % t for t in f["operands"]) if f["operands"] else "none"


GENERATED = ("<!-- Generated by docs/tools/reference.py from gen/claims.json, gen/kernels/, "
             "include/kairn/gen/, proofs/gen/, proofs/audit/, results/*/brute/, results/brute-code.json and "
             "docs/tools/reference_operations.py. Do not edit: run python3 docs/tools/reference.py. -->")

NOT_CALLED = "not yet called by the public headers"


class Site:
    def __init__(self, root, claims=None):
        self.root = root
        ops = load_operations(root)
        self.ops = ops
        self.groups = [(g, title, about) for g, title, about in ops.GROUPS]
        group_ids = {g for g, _, _ in self.groups}
        self.brute = load_brute(root)
        self.code_then = load_code(root, self.brute)
        self.bounds = load_bounds(root)
        self.statements = load_statements(root)
        self.allowed_axioms, self.audited = load_audit(root)
        self.not_judged = load_not_judged(root)
        # The generated formal models (the real one, and the IEEE one where it exists) and the
        # kernels each defines.
        self.models = []
        for f in ("Model.v", "IeeeModel.v"):
            path = os.path.join(root, "proofs", "gen", f)
            if os.path.exists(path):
                self.models.append((f, set(re.findall(r"^Definition (\w+) ", read(path), re.M))))
        self.kernels = {}
        entries = load_claims(root, claims)
        # The claims of each kernel as a run judges them (docs/tools/brute_code.py, NOT_JUDGED).
        self.claims_now = {e["name"]: BRUTE_CODE.claims_fingerprint(e) for e in entries}
        self.all_names = {e["name"] for e in entries}
        KERNEL_CLAIMS.clear()
        KERNEL_CLAIMS.update({e["name"]: e for e in entries})
        for entry in entries:
            name = entry["name"]
            if name not in ops.KERNELS:
                fail("kernel %s is not in docs/tools/reference_operations.py: add its page there (group, "
                     "title, the C++ forms that reach it)" % name)
            self.kernels[name] = Kernel(entry, load_listing(root, name))
        self.code_now = code_now(root, sorted(self.kernels))
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
        self.callers = {}
        for k in self.kernels.values():
            for callee in k.calls(self.all_names):
                self.callers.setdefault(callee, []).append(k.name)
        # The loops that public operations call (reference_operations.LOOPS), and for each kernel the
        # loops whose descriptions name it.
        self.loops = dict(getattr(ops, "LOOPS", {}))
        self.loops_of = {}
        for loop in self.loops:
            for name in fold_kernels(root, loop):
                if name in self.all_names and loop not in self.loops_of.get(name, []):
                    self.loops_of.setdefault(name, []).append(loop)
        self.ce_of = {k.listing["fields"]["ce_variant"]: k.name for k in self.kernels.values()
                      if k.listing["fields"].get("ce_variant")}
        # The cores of full kernels, and the full kernels that build on a finite kernel.
        self.core = {}
        for k in self.kernels.values():
            for e in k.entry["ensures"]:
                if e["kind"] == "extends":
                    if e["core"] not in self.kernels:
                        fail("kernel %s: its core %s is not a kernel of gen/claims.json" % (k.name, e["core"]))
                    if self.kernels[e["core"]].extended:
                        fail("kernel %s: its core %s is not of the finite domain" % (k.name, e["core"]))
                    if e["lead"] not in KNOWN_LEADS:
                        fail("kernel %s: the lead %r of an extends claim has no template" % (k.name, e["lead"]))
                    self.core[k.name] = e["core"]
        self.full_of = {}
        for k in self.kernels.values():
            if k.extended and not k.finite_reading:
                for callee in k.calls(self.all_names):
                    if not self.kernels[callee].extended:
                        self.full_of.setdefault(callee, []).append(k.name)

    def generated(self):
        return GENERATED

    def same_code(self, doc, name):
        """Whether the runs of a stored summary ran the code that the kernel has now: the
        fingerprint of its code at every commit the summary names is that of the tree."""
        now = self.code_now.get(name)
        return now is not None and all(self.code_then[c]["code"].get(name) == now for c in doc["commit"])

    def same_claims(self, doc, name):
        """Whether the runs of a stored summary judged the claims that the kernel has now: the
        fingerprint of its claims at every commit the summary names, the code it ran, claims
        included (tests/brute/brute.py, CODE_PATHS), is that of the claims now."""
        now = self.claims_now.get(name)
        return now is not None and all(self.code_then[c]["claims"].get(name) == now for c in doc["commit"])

    def link(self, name, frm=""):
        if name in self.kernels:
            return "[`%s`](%s%s.md)" % (name, frm, name)
        return "`%s`" % name

    def not_called(self, name):
        """An entry kernel with no form in the table and in no loop that public operations call: one the
        public headers do not call yet."""
        return (not self.ops.KERNELS[name]["forms"] and name not in self.loops_of
                and self.kernels[name].listing["fields"].get("entry") == "yes")

    def in_loops(self, name):
        """The sentence of a kernel that is part of loops that public operations call."""
        return " It is part of %s." % "; and of ".join(
            "the loop `%s`, called by %s" % (l, self.loops[l]) for l in self.loops_of[name])

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
        if k.extended and k.finite_reading:
            status = "%s for finite operands · %s for infinite and NaN operands" % (
                "proved" if k.proved else "**UNVERIFIED**", "proved" if k.ieee_proved else "**UNVERIFIED**")
        else:
            status = "proved" if k.proved else "**UNVERIFIED**"
        w("Kernel `%s` · %s · [all operations](index.md) · [how to read this page](reading.md)" % (name, status))
        w("")
        if not k.proved:
            calls = ("An operation that calls this kernel compiles only with the marker `kairn::unverified` on "
                     "an operand, and `kairn::traits` exports no constants for it"
                     if p["forms"] else "No public operation calls it yet")
            if k.extended:
                tested = "Rocq has not checked a proof of it"
            elif name in self.not_judged:
                # On the list of what the oracle does not judge yet (tests/CMakeLists.txt): the
                # generator's tests test it, and no cross-check against the oracle is registered.
                tested = ("the generator's tests test it, but the oracle does not judge it yet (it is on the list "
                          "`KAIRN_NOT_YET_CROSS_CHECKED` of `tests/CMakeLists.txt`) and Rocq has not checked a "
                          "proof of it")
            else:
                tested = "the oracle tests it, but Rocq has not checked a proof of it"
            w("**UNVERIFIED: no proof is checked.** The statement below is a target: %s. %s "
              "([What holds today](../getting-started/guarantees.md#proved-and-unverified))." % (tested, calls))
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
        w(self.cpp(k, p))
        w("")

        # Requirements and guarantees: on finite operands where that reading exists, otherwise the
        # statement in the IEEE model, which is then the only one.
        w("## Requires")
        w("")
        for line in (self.finite_requirements(k) if k.finite_reading else self.extended_requirements(k)):
            w("- " + line + ".")
        w("")
        w("## Guarantees" if k.proved else "## Target (not proved)")
        w("")
        if k.finite_reading:
            w("When the requirements hold and no operation of the kernel overflows:")
            w("")
            for x in k.finite_entries:
                w("- " + k.finite_bullet(x) + ".")
            w("")
            if any(k.bound_tex(x) is not None for x in k.errors):
                w(self.constants(k))
            outward = [x for x in k.finite_entries if x["kind"] == "outward"]
            if outward:
                w(self.outward_constants(k, outward[0]))
            users = k.constants_of()
            if users:
                w(self.ball_constants(k, users))
            w(self.precision(k, extended=False))
        else:
            w("For operands that satisfy the requirements, finite, infinite or NaN:")
            w("")
            w(self.extended_statement(k))
            tights = [x["tight"] for x in e["ensures"] if x.get("tight", {}).get("kind") == "outward"] + \
                [x for x in e["ensures"] if x["kind"] == "outward"]
            if tights:
                w(self.outward_constants(k, tights[0]))
            if any(k.bound_tex(x) is not None for x in k.errors):
                w(self.constants(k))
            w(self.precision(k, extended=True))
        w("")

        # Status.
        w("## Status")
        w("")
        w(self.status(k))
        w("")

        # The statement on infinite and NaN operands of a kernel that also has one on finite operands.
        if k.extended and k.finite_reading:
            w("## Infinite and NaN operands")
            w("")
            w("The statement above is about finite operands. The claims also say what the kernel returns "
              "when its operands may be infinite or NaN. That statement requires:")
            w("")
            for line in self.extended_requirements(k):
                w("- " + line + ".")
            w("")
            w("and then:")
            w("")
            w(self.extended_statement(k))
            w(self.precision(k, extended=True))
            w("")
            w(self.ieee_status(k))
            w("")

        # The axioms of the proved theorems.
        axioms = self.axioms(k)
        if axioms:
            w("## Axioms")
            w("")
            w(axioms)
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
        models = ["`proofs/gen/%s`" % f for f, names in self.models if name in names]
        made = ("the C++ and the formal model%s (%s) are" % ("s" if len(models) > 1 else "", ", ".join(models))
                if models else "the C++ is")
        w("From [`gen/kernels/%s.kernel`](%s/blob/main/gen/kernels/%s.kernel), the description %s generated "
          "from.%s Each line is one operation of `T`; one that rounds rounds to nearest, and `prod(a, b)` is "
          "$\\mathrm{RN}(ab)$, written as a fused multiply-add with a zero addend "
          "([the kernel IR](../developer/architecture.md#the-kernel-ir))." % (
              name, REPO_URL, name, made, "" if models else " The generator prints no formal model of it yet."))
        calls = k.calls(self.all_names)
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
        for line in self.not_claimed(k):
            w("- " + line)
        w("")
        return "\n".join(out)

    def cpp(self, k, p):
        name = k.name
        if p["forms"]:
            rows = ["| Form | Operands | Result | Note |", "|---|---|---|---|"]
            for f in p["forms"]:
                rows.append("| `%s` | %s | `%s` | %s |" % (f["code"], operand_types(f), f["result"], f["note"] or ""))
            constructors = [f for f in p["forms"] if re.match(r"(Expansion|Ball)<", f["code"])]
            if all(f["code"].startswith("traits<") for f in p["forms"]):
                # The bounds as functions of the length: static member functions of kairn::traits.
                text = "\n".join(rows) + "\n\n" + (
                    "`T` is `float` or `double`; `kairn::traits<T>` is also `kairn::traits<float>`, "
                    "`kairn::traits<double>` and `kairn::traits<Expansion<T, 1>>`; header `kairn/kairn.hpp` "
                    "(`traits.hpp`). `constexpr`, with the same bits at compile time and at run time; where "
                    "the mask is false the result's `unit` and `tiny` are $+\\infty$, which claims nothing, "
                    "and in a constant expression the call does not compile ([Functions on "
                    "arrays](batch.md#the-bound-as-a-function-of-the-length)).")
            elif any(t.startswith("Accumulator") for f in p["forms"] for t in f["operands"]):
                # The accumulator (kairn/accumulator.hpp): member functions, no marker.
                text = "\n".join(rows) + "\n\n" + (
                    "`T` is `float` or `double`; `A` and `B` are accumulators, `kairn::Accumulator<T, k>`, header "
                    "`kairn/accumulator.hpp`, which `kairn/kairn.hpp` includes. They take no marker: an "
                    "operation of an accumulator compiles only while its kernels are proved "
                    "([The accumulator](accumulator.md)).")
            elif any("SoAView" in t for f in p["forms"] for t in f["operands"]):
                # The functions on arrays (kairn/batch.hpp): a header of their own, and no marker.
                # A row of another header (an operator of Packed<T, 1> over the same step) names it.
                packed = any(t.startswith("Packed") for f in p["forms"] for t in f["operands"])
                text = "\n".join(rows) + "\n\n" + (
                    "`T` is `float` or `double`; the functions %sare in namespace `kairn`, header "
                    "`kairn/batch.hpp`, which `kairn/kairn.hpp` does not include; a view of `T` is taken "
                    "where the table writes a view of `const T`. They take no marker: a function on arrays "
                    "compiles only while the kernels of its loop are proved ([Functions on arrays](batch.md)).%s"
                    % ("on arrays " if packed else "",
                       " The operators of `Packed<T, 1>` are in `kairn/packed.hpp`, which `kairn/kairn.hpp` "
                       "does not include either, and take no marker ([Packed](packed.md#one-limb))."
                       if packed else ""))
            else:
                text = "\n".join(rows) + "\n\n" + (
                    "`T` is `float` or `double`; the operations are in namespace `kairn`, header "
                    "`kairn/kairn.hpp`. The operators and functions also accept the marker `kairn::unverified` "
                    "on an operand, which they need while the kernel is UNVERIFIED%s." % (
                        " (a constructor does not take it)" if constructors else ""))
            if p["note"]:
                text += "\n\n" + p["note"]
            return text
        if self.not_called(name):
            text = "**%s.** No public operation computes this kernel yet." % NOT_CALLED.capitalize()
            cores = [self.core[name]] if name in self.core else [
                c for c in k.calls(self.all_names) if not self.kernels[c].extended]
            called = [c for c in cores if self.ops.KERNELS[c]["forms"]]
            full = [f for f in self.full_of.get(name, []) if self.ops.KERNELS[f]["forms"]]
            if full:
                text += (" The operations of the public headers call %s, which computes this kernel and then "
                         "the fix-up of its results." % " and ".join(self.link(f) for f in full))
            elif called:
                text += " The operations of the public headers call its core, %s, instead." % " and ".join(
                    self.link(c) for c in called)
            elif self.callers.get(name):
                # A building block made public by Milestone 2 (two_prod), which kernels also call.
                text += " It is part of %s." % ", ".join(self.link(c) for c in self.callers[name])
            if p["note"]:
                text += " " + p["note"]
            return text
        callers = self.callers.get(name, [])
        text = "No public operation computes this kernel on its own."
        if callers:
            text += " It is part of %s." % ", ".join(self.link(c) for c in callers)
        if name in self.loops_of:
            text += self.in_loops(name)
        if name in self.ce_of:
            text += " It replaces %s in constant evaluation, where there is no fused multiply-add." % (
                self.link(self.ce_of[name]))
        return text

    def finite_requirements(self, k):
        return ["Every limb of every operand is a finite number of `T`"] + [
            line for kind, args in k.requires for line in k.finite_requirement(kind, args)]

    def extended_requirements(self, k):
        """In the order of the inputs: each requirement where its first input is, and each one-limb
        input that no requirement constrains, which may then be any value of T."""
        lines = [(min(k.inputs.index(a) for a in args), k.extended_requirement(kind, args))
                 for kind, args in k.requires]
        for a in k.extended_free_inputs():
            lines.append((k.inputs.index(a), ("$%s$ is a mask, true or false" if a in k.mask_inputs else
                                              "$%s$ is any value of `T`: a number, $\\pm\\infty$ or a NaN"
                                              if len(k.limbs(a)) == 1 else
                                              "every limb of $%s$ is any value of `T`: a number, $\\pm\\infty$ "
                                              "or a NaN") % name_tex(a)))
        return [text for _, text in sorted(lines, key=lambda x: x[0])]

    # The statement in the extended domain, as a Markdown list.
    def extended_statement(self, k):
        e = k.entry
        kinds = [x["kind"] for x in e["ensures"]]
        lines = []
        exact_kinds = [x for x in e["ensures"] if x["kind"] in ("normalized", "error")]
        represents = [x for x in e["ensures"] if x["kind"] == "represents"]
        # Which value comes out, for every canonical operand, when the claims say it (represents);
        # otherwise only that it is canonical. Then the statement on finite operands, which holds
        # when everything is finite.
        for x in represents:
            lines.extend(self.extended_represents(k, x))
        if exact_kinds:
            outs = []
            for x in exact_kinds:
                if x["of"] not in outs:
                    outs.append(x["of"])
            several = [o for o in outs if len(k.limbs(o)) > 1]
            if not represents and several:
                lines.append("$%s$ %s canonical." % ("$, $".join(name_tex(o) for o in several),
                                                      "is" if len(several) == 1 else "are"))
            lines.append("When every operand and %s are finite, the statement on finite operands holds:" % (
                " and ".join("$%s$" % name_tex(o) for o in outs)))
            for x in exact_kinds:
                lines.append("    - " + k.finite_bullet(x) + ".")
        for x in e["ensures"]:
            kind = x["kind"]
            if kind in ("normalized", "error", "represents"):
                continue
            if kind == "predicate":
                lines.append("$%s$ is true exactly when $%s$ holds between the two values as extended real "
                             "numbers ($-\\infty$ below every real number, $+\\infty$ above), and false when an "
                             "operand is a NaN." % (name_tex(x["of"]), k.relation(x)))
            elif kind == "rounded":
                lines.extend(self.extended_rounded(k, x))
            elif kind == "upper":
                lines.extend(self.extended_upper(k, x))
            elif kind == "neighbor":
                lines.extend(self.extended_neighbor(k, x))
            elif kind == "bound":
                lines.extend(self.extended_bound(k, x))
            elif kind == "extends":
                lines.extend(self.extended_extends(k, x))
            elif kind == "encloses":
                lines.extend(self.extended_encloses(k, x))
            elif kind == "makes_ball":
                lines.extend(self.extended_makes_ball(k, x))
            elif kind == "finite_or_nan" and ("if" in x or "steps" in x or "if_all" in x):
                # The finish of a fold of maxima: the value stepped up, under the mask of the state.
                r, f, s = name_tex(x["of"]), name_tex(x["flag"]), tex(k.value)
                for _ in range(x.get("steps", 0)):
                    s = "\\mathrm{succ}(%s)" % s
                gate = ("$%s$ is true and " % name_tex(x["if"])) if "if" in x else ""
                if "if_all" in x:      # the finish of the product of two BallVectors: several masks
                    gate = " and ".join("$%s$" % name_tex(n) for n in x["if_all"]) + " are true and "
                sign = " and not negative (a zero of either sign is not)" if x.get("nonneg") else ""
                lines += ["$%s$ is true exactly when %s$%s$ is finite%s." % (f, gate, s, sign),
                          "When it is, $%s = %s$." % (r, s),
                          "Otherwise $%s$ is a NaN." % r]
            elif kind == "finite_or_nan":
                s, r, f = tex(k.value), name_tex(x["of"]), name_tex(x["flag"])
                lead = k.limbs(k.value[1])[0]
                lines += ["$%s$ is true exactly when $%s$ is finite." % (f, name_tex(lead)),
                          "When it is, $%s = %s$, limb for limb." % (r, s),
                          "Otherwise every limb of $%s$ is a NaN." % r]
            elif kind == "makes_interval":
                lines.extend(self.extended_makes_interval(k, x))
            elif kind == "encloses_interval":
                lines.extend(self.extended_interval(k, x))
            elif kind == "set_bound":
                lines.extend(self.extended_set_bound(k, x))
            elif kind == "outward":
                lines.extend(self.extended_outward(k, x))
            elif kind == "interval_set":
                lines.extend(self.extended_interval_set(k, x))
            elif kind == "ball_of_interval":
                lines.extend(self.extended_ball_of_interval(k, x))
            elif kind == "interval_of_ball":
                lines.extend(self.extended_interval_of_ball(k, x))
            elif kind == "splits":
                lines.extend(self.extended_splits(k, x))
            elif kind in ("certain", "trit"):
                lines.extend(self.extended_set_predicate(k, x))
            elif kind == "ball_set":
                lines.extend(self.extended_ball_set(k, x))
            elif kind == "ball_splits":
                lines.extend(self.extended_ball_splits(k, x))
            else:
                fail("kernel %s: the claim kind %r has no reading in the extended domain" % (k.name, kind))
        if not kinds:
            fail("kernel %s claims nothing" % k.name)
        return "\n".join("- " + l if not l.startswith("    ") else l for l in lines) + "\n"

    def leading(self, k, node):
        """The value expression with each operand of several limbs replaced by its leading limb."""
        return substitute(node, {i: k.lead_limb(i) for i in k.inputs if len(k.limbs(i)) > 1})

    def extended_rounded(self, k, x):
        mode = x["mode"]
        if mode not in KNOWN_MODES:
            fail("kernel %s: the rounding mode %r has no template" % (k.name, mode))
        t, v = name_tex(x["of"]), tex(k.value)
        what = {
            "nearest": "$%s = \\mathrm{RN}(%s)$, the nearest number of `T` with ties to even, or $\\pm\\infty$ "
                       "when $\\lvert %s\\rvert \\ge \\Omega + \\tfrac12\\,\\mathrm{ulp}(\\Omega)$" % (t, v, v),
            "down": "$%s$ is the largest number of `T` not above $%s$, or $-\\infty$ when $%s < -\\Omega$" % (t, v, v),
            "up": "$%s$ is the smallest number of `T` not below $%s$, or $+\\infty$ when $%s > \\Omega$" % (t, v, v),
        }[mode]
        when = k.when_tex(x)
        zero = self.zero_factor(k, x)
        return zero + ["If every operand is finite%s: %s ($\\Omega$ is the largest finite number of `T`)." % (
                    " and " + when[len("when "):] if when else "", what),
                "If an operand is infinite or NaN%s: $%s = %s$%s." % (
                    " and none is a zero" if zero else "",
                    t, tex(self.leading(k, k.value)), ", as `T` computes it" if has_binary(k.value) else "")]

    def zero_factor(self, k, x):
        """The line of zero_factor (Milestone 2, mul_dir_1): a zero operand gives zero, 0 times
        infinity included; none without the field."""
        if not x.get("zero_factor"):
            return []
        return ["If an operand is a zero: $%s$ is a zero, whatever the other operand, $\\pm\\infty$ included "
                "($0 \\cdot \\infty = 0$, the product of two bounds in interval arithmetic)." % name_tex(x["of"])]

    def extended_neighbor(self, k, x):
        r, a = name_tex(x["of"]), tex(k.value)
        if x["side"] == "up":
            return ["$%s$ is the next number of `T` above $%s$: for a finite $%s$ the smallest number of `T` "
                    "above it, $+\\infty$ above $\\Omega$ and $\\eta$ above either zero; $-\\Omega$ for "
                    "$%s = -\\infty$; $+\\infty$ for $%s = +\\infty$; a NaN for a NaN." % (r, a, a, a, a)]
        return ["$%s$ is the next number of `T` below $%s$: for a finite $%s$ the largest number of `T` "
                "below it, $-\\infty$ below $-\\Omega$ and $-\\eta$ below either zero; $\\Omega$ for "
                "$%s = +\\infty$; $-\\infty$ for $%s = -\\infty$; a NaN for a NaN." % (r, a, a, a, a)]

    def extended_bound(self, k, x):
        r, v, n = name_tex(x["of"]), tex(k.value), x["steps"]
        below = x["side"] == "below"
        if below:
            rounding = ("the largest number of `T` not above $%s$, which is $\\Omega$ when $%s > \\Omega$ and "
                        "$-\\infty$ when $%s < -\\Omega$" % (v, v, v))
        else:
            rounding = ("the smallest number of `T` not below $%s$, which is $+\\infty$ when $%s > \\Omega$ and "
                        "$-\\Omega$ when $%s < -\\Omega$" % (v, v, v))
        zero = self.zero_factor(k, x)
        return zero + ["If every operand is finite: $%s %s %s$, and $%s$ is at most %d step%s of `T` %s %s (a step %s "
                "$%s\\Omega$ gives $%s\\infty$)." % (
                    r, "\\le" if below else "\\ge", v, r, n, "" if n == 1 else "s", "below" if below else "above",
                    rounding, "below" if below else "above", "-" if below else "", "-" if below else "+"),
                "If an operand is infinite or NaN%s: $%s = %s$, as `T` computes it." % (
                    " and none is a zero" if zero else "", r, tex(k.value))]

    def extended_upper(self, k, x):
        r, v = name_tex(x["of"]), tex(k.value)
        gaps = num_tex(fractions.Fraction(x["gaps"]))
        nan = "an operand is a NaN" + (" or the product is $0 \\cdot \\infty$" if has_product(k.value) else "")
        return ["$%s$ is a NaN exactly when %s." % (r, nan),
                "Otherwise $%s \\ge %s$ (so $%s = +\\infty$ when an operand is $+\\infty$), and when $%s$ is "
                "finite it exceeds $%s$ by at most $%s$ gaps of the format." % (r, v, r, r, v, gaps)]

    def conditions(self, k, conds):
        """The finite_when conditions as TeX, and the note on e_max, or None for an empty list."""
        if not conds:
            return None
        parts = []
        for c in conds:
            node = k.expr(c["abs_le"], "finite_when", set(k.inputs))
            parts.append("$\\lvert %s\\rvert \\le %s$" % (tex(node), power_tex(c["exp"])))
        return " and ".join(parts)

    def threshold_note(self, conds):
        exps = sorted({c["exp"] for c in conds}, reverse=True)
        values = []
        for e in exps:
            values.append("$%s$ is %s" % (power_tex(e), ", ".join(
                "$2^{%d}$ for `%s`" % (q + p + e, ctype) for _, ctype, p, q in FORMATS)))
        return ("The conditions are on the exact values of the operands, and $2^{e_{\\max}}$ is the overflow "
                "threshold of `T`, just above its largest finite number: %s." % "; ".join(values))

    def extended_extends(self, k, x):
        core = self.kernels[self.core[k.name]]
        view = renamed_core(core, k)
        w = x["of"]
        k.is_two_limbs(w, "extends(%s)" % w)
        w0 = name_tex(k.lead_limb(w))
        v = tex(k.value)
        lines = ["**F1.** $%s$ is canonical: finite and normalized, or $(\\pm\\infty, \\pm 0)$, or "
                 "$(\\mathrm{NaN}, \\mathrm{NaN})$." % name_tex(w)]
        lines.append("**F2.** If $%s$ is finite, then every operand is finite and $%s$ satisfies the statement "
                     "of its core, %s:" % (w0, name_tex(w), self.link(core.name)))
        for c in view.entry["ensures"]:
            lines.append("    - " + view.finite_bullet(c) + ".")
        conds = self.conditions(k, x["finite_when"])
        if conds:
            lines.append("**F3.** If every operand is finite and %s, then $%s$ is finite. %s" % (
                conds, w0, self.threshold_note(x["finite_when"])))
        else:
            lines.append("**F3.** No condition under which $%s$ is finite is claimed yet: the claims list none, "
                         "which does not say that it always is." % w0)
        lines.append("**F4.** If every operand is finite and $%s$ is not, then $%s = (\\pm\\infty, 0)$, with the "
                     "sign of $%s$." % (w0, name_tex(w), v))
        if len(k.inputs) != 2:
            fail("kernel %s: an extends claim with %d inputs has no template" % (k.name, len(k.inputs)))
        a, b = (name_tex(k.lead_limb(i)) for i in k.inputs)
        op = "%s %s %s" % (a, KNOWN_LEADS[x["lead"]], b)
        example = {"add": "$+\\infty + 1 = +\\infty$, $+\\infty + (-\\infty) = \\mathrm{NaN}$",
                   "sub": "$+\\infty - 1 = +\\infty$, $+\\infty - (+\\infty) = \\mathrm{NaN}$",
                   "mul": "$+\\infty \\cdot 2 = +\\infty$, $0 \\cdot \\infty = \\mathrm{NaN}$"}[x["lead"]]
        lines.append("**F5.** If an operand is not finite, then $%s$ is the canonical form of $%s$ computed "
                     "in `T`: $(\\pm\\infty, 0)$ for an infinity, $(\\mathrm{NaN}, \\mathrm{NaN})$ for a NaN (for "
                     "example %s)." % (name_tex(w), op, example))
        return lines

    def extended_encloses(self, k, x):
        cw, rw = name_tex(x["center"]), name_tex(x["radius"])
        balls = x["balls"]
        ball_inputs = {cr[f] for cr in balls.values() for f in ("center", "radius")}
        scalars = [i for i in k.inputs if i not in ball_inputs]
        names = [name_tex(b).upper() for b in balls]
        s = k.expr(x["set"], "encloses", set(balls) | set(k.inputs))
        each = ", ".join("$%s \\in %s$" % (name_tex(b), name_tex(b).upper()) for b in balls)
        finite_ops = "%s %s finite ball%s" % (
            " and ".join("$%s$" % n for n in names), "are" if len(names) > 1 else "is a",
            "s" if len(names) > 1 else "") + "".join(" and $%s$ is finite" % name_tex(a) for a in scalars)
        lines = ["**B1.** The result $Z$, of center $%s$ and radius $%s$, is a canonical ball: a finite ball, "
                 "the whole line (center 0, radius $+\\infty$), or the empty set (every limb a NaN)." % (cw, rw),
                 "**B2.** $Z$ is empty exactly when %s." % (
                     "an operand ball is empty" if len(balls) > 1 else "$%s$ is empty" % names[0]),
                 "**B3.** If $Z$ is a finite ball, then %s, and %s." % (finite_ops, k.encloses_text(
                     dict(x, center=x["center"], radius=x["radius"])))]
        if "exact_when" in x:
            lines.append("**Exact.** If $Z$ is a finite ball and %s, then $Z$ is exactly the set of the $%s$: every "
                         "number within $%s$ of $%s$ is one of them." % (
                             k.exact_tex(x["exact_when"]), tex(s), rw, cw))
        conds = self.conditions(k, x.get("finite_when", []))
        if conds:
            lines.append("**B4.** If %s and %s, then $Z$ is a finite ball. %s" % (
                finite_ops, conds, self.threshold_note(x["finite_when"])))
        else:
            lines.append("**B4.** No condition under which $Z$ is a finite ball is claimed yet: the claims list "
                         "none, which does not say that it always is.")
        lines.append("It follows that in every case $Z$ contains $%s$ for every %s: the whole line contains every "
                     "real number, and an empty operand has no points." % (tex(s), each))
        return lines

    def extended_represents(self, k, x):
        o = x["of"]
        k.is_two_limbs(o, "represents(%s)" % o)
        v = tex(k.value)
        o0, o1 = (name_tex(l) for l in k.limbs(o))
        return ["$%s$ is canonical and is $%s$ exactly: when $%s$ is finite, $%s$ is finite and normalized "
                "with $%s + %s = %s$; when $%s = \\pm\\infty$, $%s = (\\pm\\infty, 0)$; when $%s$ is a NaN, "
                "$%s = (\\mathrm{NaN}, \\mathrm{NaN})$." % (
                    name_tex(o), v, v, name_tex(o), o0, o1, v, v, name_tex(o), v, name_tex(o))]

    def extended_makes_interval(self, k, x):
        lo, hi = name_tex(x["from"]["lower"]), name_tex(x["from"]["upper"])
        zl, zu = name_tex(x["lower"]), name_tex(x["upper"])
        return ["The result $Z = [%s, %s]$ is a canonical interval." % (zl, zu),
                "If a bound is a NaN, whatever the other, or both are the same infinity ($[+\\infty, +\\infty]$, "
                "$[-\\infty, -\\infty]$): $Z$ is the whole line, $[-\\infty, +\\infty]$.",
                "Otherwise, if the bounds are reversed, $%s > %s$ ($[+\\infty, -\\infty]$, and $%s = +\\infty$ or "
                "$%s = -\\infty$ with the other finite, among them): $Z$ is the empty set, $(+\\infty, -\\infty)$." % (
                    lo, hi, lo, hi),
                "Otherwise ($%s \\le %s$, $%s < +\\infty$ and $%s > -\\infty$): $Z$ is $[%s, %s]$, the same extended "
                "real numbers (a zero may change its sign)." % (lo, hi, lo, hi, lo, hi)]

    def interval_set(self, k, x):
        names = list(x["intervals"])
        s = tex(k.expr(x["set"], "encloses_interval", set(names)))
        each = ", ".join("$%s \\in %s$" % (name_tex(n), name_tex(n).upper()) for n in names)
        return s, each, names

    def extended_interval(self, k, x):
        """I1 to I5 of milestone2.md, "What is stated of an interval kernel"."""
        s, each, names = self.interval_set(k, x)
        big = [name_tex(n).upper() for n in names]
        zl, zu = name_tex(x["lower"]), name_tex(x["upper"])
        ops = " and ".join("$%s$" % n for n in big)
        lines = ["**I1.** The result $Z = [%s, %s]$ is a canonical interval." % (zl, zu),
                 "**I2.** $Z$ is empty exactly when %s." % (
                     "an operand is" if len(names) > 1 else "$%s$ is" % big[0]),
                 "**I3.** $Z$ contains $%s$ for every %s, unbounded operands included (their members are real "
                 "numbers)." % (s, each)]
        t = x["tight"]
        members = ", ".join("%s \\in %s" % (name_tex(n), name_tex(n).upper()) for n in names)
        rng = ("$\\ell$ and $h$ are the greatest lower bound and the least upper bound of the exact range "
               "$\\{\\, %s : %s \\,\\}$, as extended real numbers" % (s, members))
        if t["kind"] == "exact":
            lines.append("**I4.** For nonempty %s, where %s: $%s = \\ell$ and $%s = h$, exactly." % (ops, rng, zl, zu))
        elif t["kind"] == "rounded":
            steps = t.get("steps", 0)
            text = ("**I4.** For nonempty %s, where %s: %s" % (ops, rng, (
                "$%s = \\mathrm{RD}(\\ell)$ and $%s = \\mathrm{RU}(h)$, the roundings in the format with overflow "
                "(an infinite bound of the range is returned as such)" % (zl, zu)) if not steps else (
                "$%s$ is $\\mathrm{RD}(\\ell)$ or at most %d step%s of `T` below it, and $%s$ is $\\mathrm{RU}(h)$ "
                "or at most as many above it" % (zl, steps, "" if steps == 1 else "s", zu))))
            if t.get("when") == "product_large":
                text += ("; exactly $\\mathrm{RD}(\\ell)$ and $\\mathrm{RU}(h)$ when each product of a finite bound "
                         "of $%s$ and a finite bound of $%s$ is zero or at least $\\eta/(2u^2)$ in magnitude" % tuple(big))
            lines.append(text + ".")
        else:
            conds = ", ".join("for the %s bound when %s" % (side, k.exact_tex(c))
                              for side, c in t.get("exact_when", {}).items())
            lines.append("**I4.** For bounded %s and a bounded $Z$, where %s: $\\ell - %s \\le A\\,\\lvert \\ell\\rvert + "
                         "B$ and $%s - h \\le A\\,\\lvert h\\rvert + B$, with the constants $A$ and $B$ below. A bound "
                         "of $Z$ is the bound of the range exactly %s. For nonempty operands, an infinite bound of the "
                         "range is returned as such." % (ops, rng, zl, zu, conds or "in no case claimed"))
        if x.get("zero_factor"):
            lines.append("**I6.** For nonempty %s: if an operand is $[0, 0]$, $Z$ is $[0, 0]$, the other operand "
                         "unbounded included ($0 \\cdot \\infty = 0$, the rule of interval arithmetic)." % ops)
        cs = []
        for c in x["bounded_when"]:
            cs.append("$\\lvert z\\rvert \\le %s$" % ("\\Omega" if c.get("omega") else power_tex(c["exp"])))
        if cs:
            lines.append("**I5.** For bounded %s, $Z$ is bounded %s every member $z$ of the exact range satisfies %s.%s" % (
                ops, "exactly when" if x.get("bounded_exactly") else "when", " and ".join(cs),
                "" if all(c.get("omega") for c in x["bounded_when"]) else
                " " + self.threshold_note([c for c in x["bounded_when"] if not c.get("omega")])))
        else:
            lines.append("**I5.** No condition under which $Z$ is bounded is claimed.")
        return lines

    def extended_outward(self, k, x):
        """outward in the extended domain (stage B1, mul_ext_2_2)."""
        r, v = k.out_tex(x["of"]), tex(k.value)
        below = x["side"] == "below"
        zero = self.zero_factor(k, x)
        return zero + ["$%s$ is never a NaN." % r,
                       "If an operand is infinite%s: $%s = %s$ as `T` computes it on the leading limbs, the infinity "
                       "of the sign of the product." % (" and none is a zero" if zero else "", r, v),
                       "If every operand is finite: $%s %s %s$ (an infinite $%s$ is $%s\\infty$), and when $%s$ is "
                       "finite, $\\lvert %s - %s\\rvert \\le A\\,\\lvert %s\\rvert + B$, with the constants "
                       "$A$ and $B$ below." % (r, "\\le" if below else "\\ge", v, r, "-" if below else "+", r, r,
                                              parenthesized(k.value), v)]

    def extended_interval_set(self, k, x):
        """The hull or the intersection of two intervals (stage B1)."""
        (a, ba), (b, bb) = x["intervals"].items()
        A, B = name_tex(a).upper(), name_tex(b).upper()
        zl, zu = name_tex(x["lower"]), name_tex(x["upper"])
        al, au, bl, bu = (name_tex(n) for n in (ba["lower"], ba["upper"], bb["lower"], bb["upper"]))
        lines = ["The result $Z = [%s, %s]$ is a canonical interval." % (zl, zu)]
        if x["set"] == "union":
            lines += ["$Z$ is empty exactly when $%s$ and $%s$ both are." % (A, B),
                      "Otherwise $Z$ is the smallest interval that contains $%s \\cup %s$, exactly: its lower bound "
                      "is the smaller of the lower bounds of the nonempty operands, its upper bound the larger of "
                      "their upper bounds ($[%s, %s]$ with $\\min(%s, %s)$ and $\\max(%s, %s)$ when both are "
                      "nonempty); the hull with the empty set is the other operand." % (A, B, zl, zu, al, bl, au, bu)]
        else:
            lines += ["$Z$ is empty exactly when no real number is a member of both: when an operand is empty, or "
                      "$\\max(%s, %s) > \\min(%s, %s)$." % (al, bl, au, bu),
                      "Otherwise $Z = %s \\cap %s$, exactly: $%s = \\max(%s, %s)$ and $%s = \\min(%s, %s)$; the "
                      "intersection with the whole line is the other operand." % (A, B, zl, al, bl, zu, au, bu)]
        return lines

    def extended_ball_of_interval(self, k, x):
        """A ball made from an interval (stage B1): the midpoint and radius, or a canonical ball."""
        lo, hi = name_tex(x["from"]["lower"]), name_tex(x["from"]["upper"])
        c, r = k.out_tex(x["center"]), name_tex(x["radius"])
        rel, absolute = (tex(parse(x[key], "kernel %s, %s" % (k.name, key), {"u", "eta"}, constants=True)) for key in ("rel", "abs"))
        mid = "\\tfrac{%s + %s}{2}" % (lo, hi)
        bounded = ("If $[%s, %s]$ is bounded: $%s$ and $%s$ are finite, $%s \\le %s \\le %s$, "
                   "$\\lvert %s - %s\\rvert \\le %s\\,\\lvert %s\\rvert + %s$, and $[%s - %s, %s + %s] "
                   "\\supseteq [%s, %s]$%s." % (
                       lo, hi, c, r, lo, c, hi, c, mid, rel, mid, absolute, c, r, c, r, lo, hi,
                       (": $%s$ is the smallest number of `T` with that property, "
                        "$\\mathrm{RU}(\\max(%s - %s, %s - %s))$" % (r, c, lo, hi, c)) if x.get("smallest_radius") else ""))
        if "finite_when" in x:
            conds = " and ".join("$\\lvert %s\\rvert \\le 2^{e_{\\max}%s}$" % (
                name_tex(cnd["abs_le"]), "" if cnd["exp"] == 0 else "%+d" % cnd["exp"]) for cnd in x["finite_when"])
            bounded = bounded.replace("$%s$ and $%s$ are finite, " % (c, r), "$%s$ is finite, " % c)
            bounded += (" The radius $%s$ may be $+\\infty$ for a bounded interval near the top of the range (an "
                        "infinite radius contains everything); it is finite when %s." % (r, conds))
        if x["special"] == "ieee1788":
            lines = [bounded,
                     "The whole line gives $%s = 0$, $%s = +\\infty$; $[%s, +\\infty]$ with $%s$ finite gives "
                     "$%s = \\Omega$, the largest finite number of `T`, and $[-\\infty, %s]$ gives $%s = -\\Omega$, both "
                     "with $%s = +\\infty$; the empty set gives %s. These are the values of `mid` and `rad` of "
                     "IEEE 1788." % (c, r, lo, lo, c, hi, c, r,
                                     "two NaN" if len(k.limbs(x["center"])) == 1 else "a NaN in every limb")]
            if len(k.limbs(x["center"])) == 2:
                lines.append("In every case the midpoint $%s$ is a canonical number of two limbs: two NaN for the "
                             "empty set, two zeros for the whole line, $(\\pm\\Omega, +0)$ for a half-line, and a "
                             "normalized pair for a bounded interval." % c)
            return lines
        return ["The ball of center $%s$ and radius $%s$ is canonical, and empty exactly when the interval is." % (c, r),
                bounded + " It is then a finite ball.",
                "An unbounded interval gives the whole line, center 0 and radius $+\\infty$ (a ball cannot be a "
                "half-line); the empty set gives the empty ball, every limb a NaN."]

    def extended_interval_of_ball(self, k, x):
        """An interval that encloses a ball (stage B1)."""
        b, cr = next(iter(x["balls"].items()))
        zl, zu = name_tex(x["lower"]), name_tex(x["upper"])
        c, r = name_tex(cr["center"]), name_tex(cr["radius"])
        s = tex(k.expr(x["set"], "interval_of_ball", set(x["balls"]) | set(k.inputs)))
        ball = "the ball $%s$ of center $%s$ and radius $%s$" % (name_tex(b).upper(), c, r)
        steps = x["tight"].get("steps", 0)
        if x["tight"]["kind"] == "outward":
            return self.extended_interval_of_ball_outward(k, x, b, zl, zu, c, r, s, ball)
        return ["The result $Z = [%s, %s]$ is a canonical interval, empty exactly when %s is." % (zl, zu, ball),
                "$Z$ contains $%s$ for every $%s \\in %s$: the whole line gives $[-\\infty, +\\infty]$." % (
                    s, name_tex(b), name_tex(b).upper()),
                "For a finite ball: $%s = \\mathrm{RD}(%s - %s)$ and $%s = \\mathrm{RU}(%s + %s)$, the roundings in the "
                "format with overflow%s: the smallest interval of `T` that contains the ball." % (
                    zl, c, r, zu, c, r, "" if not steps else ", or at most %d step%s beyond" % (
                        steps, "" if steps == 1 else "s"))]

    def extended_interval_of_ball_outward(self, k, x, b, zl, zu, c, r, s, ball):
        """An interval of two limbs that encloses a ball (stage B2, ball_to_interval_2)."""
        t = x["tight"]
        lines = ["The result $Z = [%s, %s]$ is a canonical interval, empty exactly when %s is." % (zl, zu, ball),
                 "$Z$ contains $%s$ for every $%s \\in %s$: the whole line gives $[-\\infty, +\\infty]$." % (
                     s, name_tex(b), name_tex(b).upper()),
                 "For a finite ball and a bounded $Z$: $%s \\le %s - %s$ and $%s + %s \\le %s$, each within "
                 "$A\\,\\lvert v\\rvert + B$ of the bound $v$ ($c \\mp r$), with the constants $A$ and $B$ below." % (
                     zl, c, r, c, r, zu)]
        sides = t.get("exact_when", {})
        for side, z, v in (("lower", zl, "%s - %s" % (c, r)), ("upper", zu, "%s + %s" % (c, r))):
            if side in sides:
                lines.append("When %s, $%s = %s$ exactly." % (k.exact_tex(sides[side]), z, v))
        for cnd in x.get("bounded_when", []):
            lines.append("For a finite ball, $Z$ is bounded when every member $%s$ of the ball has $\\lvert %s\\rvert "
                         "\\le 2^{e_{\\max}%s}$." % (name_tex(b), name_tex(b), "" if cnd["exp"] == 0 else "%+d" % cnd["exp"]))
        return lines

    def extended_splits(self, k, x):
        """Two intervals that together are the operand (stage B1)."""
        lo, hi = name_tex(x["from"]["lower"]), name_tex(x["from"]["upper"])
        (al, au), (bl, bu) = ((name_tex(q["lower"]), name_tex(q["upper"])) for q in x["parts"])
        return ["$[%s, %s]$ and $[%s, %s]$ are canonical intervals." % (al, au, bl, bu),
                "If $X = [%s, %s]$ is empty, both are." % (lo, hi),
                "Otherwise neither is, $%s = %s$, $%s = %s$ and $%s = %s$: the two together are $X$, split at that "
                "point, which is in $X$." % (al, lo, bu, hi, au, bl)]

    def center_tex(self, k, name):
        """A center input or output in TeX, by its name: the page says once what a name of several
        limbs stands for."""
        return name_tex(name)

    def ball_definitions(self, k, x):
        """The balls of a ball_set claim, in words."""
        return " and ".join("$%s$ the ball of center $%s$ and radius $%s$" % (
            name_tex(n).upper(), self.center_tex(k, b["center"]), name_tex(b["radius"])) for n, b in x["balls"].items())

    def extended_ball_set(self, k, x):
        """The hull or the intersection of two balls (stage B2)."""
        (a, ba), (b, bb) = x["balls"].items()
        A, B = name_tex(a).upper(), name_tex(b).upper()
        Z = "the ball $Z$ of center $%s$ and radius $%s$" % (self.center_tex(k, x["center"]), name_tex(x["radius"]))
        lines = ["The result, %s, is a canonical ball." % Z]
        if x["set"] == "union":
            lines += ["$Z$ contains every member of $%s$ and every member of $%s$." % (A, B),
                      "$Z$ is empty exactly when $%s$ and $%s$ both are; when $%s$ is empty, $Z$ is $%s$ as it is (the "
                      "same limbs); when $%s$ is empty and $%s$ is not, $Z$ is $%s$ as it is." % (A, B, A, B, B, A, A),
                      "Not claimed: that $Z$ is the smallest such ball."]
        else:
            lines += ["$Z$ contains every real number that is a member of both $%s$ and $%s$." % (A, B),
                      "$Z$ is empty when an operand is; when $%s$ is the whole line, $Z$ is $%s$ as it is (the same "
                      "limbs); when $%s$ is the whole line and $%s$ is not, $Z$ is $%s$ as it is." % (A, B, B, A, A),
                      "Not claimed: that $Z$ is inside $%s$ or $%s$, nor that it is empty whenever they are disjoint."
                      % (A, B)]
        return lines

    def extended_ball_splits(self, k, x):
        """Two balls that cover the halves of a ball (stage B2)."""
        c, r = self.center_tex(k, x["from"]["center"]), name_tex(x["from"]["radius"])
        (ca, ra), (cb, rb) = ((self.center_tex(k, q["center"]), name_tex(q["radius"])) for q in x["parts"])
        return ["The two parts, of centers $%s$ and $%s$ and radii $%s$ and $%s$, are canonical balls." % (ca, cb, ra, rb),
                "If the ball $X$ of center $%s$ and radius $%s$ is empty, both parts are; if it is the whole line, both "
                "are the whole line." % (c, r),
                "Otherwise every real number of $[%s - %s, %s]$ is a member of the first part, and every one of "
                "$[%s, %s + %s]$ a member of the second." % (c, r, c, c, c, r),
                "Not claimed: that the parts are inside $X$, nor that their radii are close to $%s/2$." % r]

    def set_definitions(self, k, x):
        """What the sets of a certain or trit claim are, in words."""
        if "intervals" in x:
            return " and ".join("$%s = [%s, %s]$" % (name_tex(n).upper(), name_tex(b["lower"]), name_tex(b["upper"]))
                                for n, b in x["intervals"].items())
        return " and ".join("$%s$ the ball of center $%s$ and radius $%s$" % (
            name_tex(n).upper(), k.out_tex(b["center"]) if b["center"] in k.outputs else
            k.value_of(b["center"]) if len(k.limbs(b["center"])) > 1 else name_tex(b["center"]),
            name_tex(b["radius"])) for n, b in x["balls"].items())

    def set_relation(self, k, x, formula=False, negated=False):
        """The relation of a certain or trit claim, in words, or as a formula; with `negated`, its
        failure for every choice of members (the no of a trit)."""
        rel, args = x["rel"], x["args"]

        def S(n):
            return name_tex(n).upper()
        if rel in ("lt", "le", "eq"):
            sets = [a for a in args if a != "0"]
            a, b = (name_tex(n) if n != "0" else "0" for n in args)
            op = KNOWN_RELS[rel]
            body = ("\\lnot(%s %s %s)" % (a, op, b)) if negated else "%s %s %s" % (a, op, b)
            over = ", ".join("%s \\in %s" % (name_tex(n), S(n)) for n in sets)
            nonempty = " \\ne \\emptyset, ".join(S(n) for n in sets) + " \\ne \\emptyset"
            if formula:
                return "%s \\text{ and } %s \\text{ for every } %s" % (nonempty, body, over)
            return "$%s$ for every $%s$, %s not being empty" % (body, over, " and ".join("$%s$" % S(n) for n in sets))
        if rel == "member":
            t = k.value_of(args[0]) if len(k.limbs(args[0])) > 1 else name_tex(args[0])
            if formula:
                return ("%s \\notin %s" if negated else "%s \\in %s") % (t, S(args[1]))
            return "the point $%s$ is a finite number and a member of $%s$%s" % (
                t, S(args[1]), "" if not negated else " (negated)")
        X = S(args[0])
        if rel == "empty":
            return "%s = \\emptyset" % X if formula else "$%s$ is the empty set" % X
        if rel == "entire":
            return "%s = \\mathbb{R}" % X if formula else "$%s$ is the whole line" % X
        Y = S(args[1])
        if rel == "subset":
            return "%s \\subseteq %s" % (X, Y) if formula else "$%s \\subseteq %s$, every member of $%s$ a member of $%s$" % (
                X, Y, X, Y)
        if rel == "equal":
            return "%s = %s" % (X, Y) if formula else "$%s$ and $%s$ have the same members" % (X, Y)
        if rel == "interior":
            return ("%s \\subseteq \\operatorname{int} %s" % (X, Y) if formula else
                    "every member of $%s$ is in the interior of $%s$" % (X, Y))
        if rel == "disjoint":
            return "%s \\cap %s = \\emptyset" % (X, Y) if formula else "$%s$ and $%s$ have no member in common" % (X, Y)
        fail("kernel %s: the relation %r has no template" % (k.name, rel))

    def extended_set_predicate(self, k, x):
        """certain and trit: the predicates and three-valued comparisons of the enclosure interface."""
        special = ("an operand is the empty set or the whole line" +
                   (", or the point is not a finite number" if x["rel"] == "member" else ""))
        finite_ops = "every operand is finite (%s)" % (
            "a finite ball" if "balls" in x else "a bounded interval") + \
            (" and so is the point" if x["rel"] == "member" else "")
        if x["kind"] == "certain":
            m = name_tex(x["of"])
            if x.get("exact"):
                return ["$%s$ is true exactly when %s: the answer is exact." % (m, self.set_relation(k, x))]
            lines = ["$%s$ is true only if %s." % (m, self.set_relation(k, x)),
                     "When %s, it is true exactly then." % special]
            if "exact_when" in x:
                lines.append("When %s and %s, it is true exactly then." % (finite_ops, k.exact_tex(x["exact_when"])))
            else:
                lines.append("For finite operands it may be false although the relation holds, close to where it "
                             "stops holding: the answer is certain, not exact.")
            return lines
        yes, no = name_tex(x["yes"]), name_tex(x["no"])
        held = self.set_relation(k, x, formula=True)
        failed = self.set_relation(k, x, formula=True, negated=True)
        lines = ["$%s$ is true only if $%s$; $%s$ only if $%s$; never both. Both false is the answer *unknown*." % (
            yes, held, no, failed)]
        if x["rel"] in ("lt", "le", "eq"):
            lines.append("An empty operand gives *unknown*, and so does the whole line.")
        if x.get("exact"):
            lines.append("Exact: $%s$ is true exactly when $%s$, and $%s$ exactly when $%s$; *unknown* is returned "
                         "exactly when neither holds." % (yes, held, no, failed))
        else:
            lines.append("When %s, the answer is exact: each mask is true exactly when its relation holds." % special)
            if "exact_when" in x:
                lines.append("When %s and %s, the answer is exact as well." % (finite_ops, k.exact_tex(x["exact_when"])))
            else:
                lines.append("For finite operands the answer may be *unknown* although one of the relations holds, "
                             "close to where it stops holding: certain, not exact.")
        return lines

    def extended_set_bound(self, k, x):
        b = next(iter(x["balls"]))
        cr = x["balls"][b]
        x_of, below = x["of"], x["side"] == "below"
        o = name_tex(x_of)
        s = tex(k.expr(x["set"], "set_bound", set(x["balls"]) | set(k.inputs)))
        ball = "the ball $%s$ of center $%s$ and radius $%s$" % (name_tex(b).upper(), name_tex(cr["center"]),
                                                                 name_tex(cr["radius"]))
        lines = ["If %s is empty: $%s = %s\\infty$." % (ball, o, "+" if below else "-"),
                 "Otherwise $%s %s %s$ for every $%s \\in %s$: the whole line gives $%s = %s\\infty$." % (
                     o, "\\le" if below else "\\ge", s, name_tex(b), name_tex(b).upper(), o, "-" if below else "+")]
        if x.get("tight"):
            steps = x["tight"].get("steps", 0)
            lines.append("For a finite ball: $%s = \\mathrm{%s}(%s)$, the %s bound of the ball rounded %s in the "
                         "format with overflow%s." % (
                             o, "RD" if below else "RU", "%s %s %s" % (name_tex(cr["center"]), "-" if below else "+",
                                                                         name_tex(cr["radius"])),
                             "lower" if below else "upper", "down" if below else "up",
                             "" if not steps else ", or at most %d step%s beyond it" % (steps, "" if steps == 1 else "s")))
        elif len(k.limbs(cr["center"])) > 1:
            # Why no number of steps is claimed (ball_lower_as_2, ball_upper_as_2): the center is
            # rounded to T first, and one gap of T at c can be many gaps at c -+ r.
            c, r = name_tex(cr["center"]), name_tex(cr["radius"])
            v = "%s %s %s" % (c, "-" if below else "+", r)
            errors = [x for x in k.errors if x["of"] == x_of]
            lines.append("No number of steps of `T` from $\\mathrm{%s}(%s)$ is claimed: the center, of %s limbs, is "
                         "rounded to `T` before the radius is %s, which moves the bound by up to one gap of `T` at "
                         "$%s$, and when $%s$ is much smaller than $%s$ in magnitude (a radius close to "
                         "$\\lvert %s\\rvert$) that is many gaps of `T` at the result. %s" % (
                             "RD" if below else "RU", v,
                             {2: "two", 3: "three", 4: "four"}.get(len(k.limbs(cr["center"])), len(k.limbs(cr["center"]))),
                             "subtracted" if below else "added", c, v, c, c,
                             ("What is claimed of the distance is that $%s$ is on its side of every member and "
                              "within the bound above: %s." % (o, k.finite_bullet(errors[0]))) if errors else
                             "Nothing is claimed of the distance."))
        return lines

    def extended_makes_ball(self, k, x):
        frm = x["from"]
        if set(frm) == {"lower", "upper"}:
            return self.extended_ball_from_interval(k, x)
        if set(frm) != {"center", "radius"} or frm["center"] not in k.inputs or frm["radius"] not in k.inputs:
            fail("kernel %s: the from of a makes_ball claim is not a center and a radius of the inputs" % k.name)
        c, r = name_tex(frm["center"]), name_tex(frm["radius"])
        return ["The result $Z$, of center $%s$ and radius $%s$, is a canonical ball." % (
                    name_tex(x["center"]), name_tex(x["radius"])),
                "$Z$ is the empty set (every limb a NaN) when $%s$ is negative, $-\\infty$ included." % r,
                "Otherwise $Z$ is the whole line (center 0, radius $+\\infty$) when $%s$ is a NaN or $+\\infty$, or "
                "$%s$ is not finite." % (r, c),
                "Otherwise $Z$ is the ball of center $%s$ and radius $%s$, exactly." % (c, r)]

    def extended_ball_from_interval(self, k, x):
        lo, hi = name_tex(x["from"]["lower"]), name_tex(x["from"]["upper"])
        c, r = name_tex(x["center"]), name_tex(x["radius"])
        lines = ["The result $Z$, of center $%s$ and radius $%s$, is a canonical ball." % (c, r),
                 "If a bound is a NaN, whatever the other, or both are the same infinity ($[+\\infty, +\\infty]$, "
                 "$[-\\infty, -\\infty]$): $Z$ is the whole line (center 0, radius $+\\infty$).",
                 "Otherwise, if the bounds are reversed, $%s > %s$: $Z$ is the empty set (every limb a NaN)." % (lo, hi),
                 "Otherwise, if both are finite ($%s \\le %s$): $Z$ is a finite ball that contains $[%s, %s]$." % (
                     lo, hi, lo, hi)]
        if x.get("midpoint_when"):
            halves = " and ".join("$%s/2$" % name_tex(cnd["half_in_format"]) for cnd in x["midpoint_when"])
            lines.append("When moreover %s are numbers of `T`: $%s = (%s + %s)/2$ exactly and $%s = "
                         "\\mathrm{RU}((%s - %s)/2)$, the smallest radius of `T` for that center." % (
                             halves, c, lo, hi, r, hi, lo))
        if "rel" in x:
            # Stage B2 (ball_from_interval_1): the center near the midpoint, and the smallest radius.
            rel, absolute = (tex(parse(x[key], "kernel %s, %s" % (k.name, key), {"u", "eta"}, constants=True)) for key in ("rel", "abs"))
            mid = "\\tfrac{%s + %s}{2}" % (lo, hi)
            lines.append("Then $%s \\le %s \\le %s$ and $\\lvert %s - %s\\rvert \\le %s\\,\\lvert %s\\rvert + %s$%s." % (
                lo, c, hi, c, mid, rel, mid, absolute,
                (", and $%s = \\mathrm{RU}(\\max(%s - %s, %s - %s))$, the smallest radius of `T` for that center" % (
                    r, c, lo, hi, c)) if x.get("smallest_radius") else ""))
        lines.append("Otherwise ($%s \\le %s$, $%s < +\\infty$, $%s > -\\infty$, and a bound is infinite): $Z$ is the "
                     "whole line; a ball cannot be a half-line." % (lo, hi, lo, hi))
        return lines

    def outward_constants(self, k, x):
        """The constants A and B of an outward claim or tightness, as the claims write them, and their
        values per format, in units of u^2 and of the smallest normal number N."""
        cols = []
        for (p, qmin), (_, ctype, _, _) in zip(Kernel.formats(), FORMATS):
            a = claim_constant(x["rel"], "kernel %s, rel" % k.name, (p, qmin), KERNEL_CLAIMS)
            b = claim_constant(x["abs"], "kernel %s, abs" % k.name, (p, qmin), KERNEL_CLAIMS)
            u, n = fractions.Fraction(1, 2 ** p), fractions.Fraction(2) ** (qmin + p - 1)
            cols.append((ctype, a / u ** 2, b / n))
        rows = ["| | %s |" % " | ".join("`%s`" % c for c, _, _ in cols), "|---|" + "---|" * len(cols),
                "| $A / u^2$ | %s |" % " | ".join("$%s$" % approx(a, 17) for _, a, _ in cols),
                "| $B / N$ | %s |" % " | ".join("$%s$" % approx(b, 17) for _, _, b in cols)]
        return ("The constants of the bound, from `gen/claims.json`: $A$ is `%s` and $B$ is `%s`, where `up( )` is "
                "a constant as `T` rounds it up (the $E$, $G$, $H$ of a radius) and `unit( )`, `tiny( )` are the "
                "constants of the center's kernel; $N$ is the smallest normal number of `T`:\n\n%s\n" % (
                    x["rel"], x["abs"], "\n".join(rows)))

    def computes(self, k):
        e = dict(k.entry, ensures=k.finite_entries) if k.finite_reading else k.entry
        kinds = [x["kind"] for x in e["ensures"]]
        v = tex(k.value) if k.value is not None else None
        if "extends" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "extends")
            w = name_tex(x["of"])
            return ("$%s$ with results like those of `T` for infinite and NaN operands and on overflow: the "
                    "result of its core, %s, when that is finite, and otherwise a canonical infinity or NaN:"
                    "\n\n$$%s \\approx %s.$$" % (v, self.link(self.core[k.name]), w, v))
        if "finite_or_nan" in kinds and any("if" in x or "steps" in x or "if_all" in x for x in e["ensures"]):
            # The finish of a fold of maxima (architecture.md, "Folds of maxima").
            x = next(x for x in e["ensures"] if x["kind"] == "finite_or_nan")
            m, r, f = k.value[1], x["of"], x["flag"]
            s = name_tex(m)
            for _ in range(x.get("steps", 0)):
                s = "\\mathrm{succ}(%s)" % s
            gate = name_tex(x["if"]) if "if" in x else None
            when = ("\\text{when } %s \\text{ is true and } %s \\text{ is finite}" % (gate, s) if gate else
                    "\\text{when } %s \\text{ is finite}" % s)
            if "if_all" in x:
                # The finish of the product of two BallVectors (architecture.md, "Ball vectors").
                masks = " \\text{ and } ".join(name_tex(n) for n in x["if_all"])
                return ("The result of the product of two BallVectors from its radius $%s$, the mask $%s$ that every "
                        "coefficient is finite and the mask $%s$ that the bound of the dot product was given: $%s$ when "
                        "both are true and $%s$ is finite, with the flag $%s$ true; otherwise a NaN and the flag false, "
                        "and the product is the whole space:\n\n$$%s = %s \\ \\text{when } %s \\text{ are true and } %s "
                        "\\text{ is finite}, \\qquad %s = \\mathrm{NaN} \\text{ otherwise}.$$"
                        % (s, name_tex(x["if_all"][0]), name_tex(x["if_all"][1]), s, s, name_tex(f), name_tex(r), s,
                           masks, s, name_tex(r)))
            if x.get("nonneg"):
                # The finish of a constructor of a BallVector (architecture.md, "Ball vectors").
                return ("The result of the constructor of a BallVector from its radius $%s$ and the mask $%s$ that no "
                        "center was a NaN: $%s$ when $%s$ is true and $%s$ is finite and not negative, with the flag "
                        "$%s$ true; otherwise a NaN and the flag false, and the constructor returns the whole space:"
                        "\n\n$$%s = %s \\ %s \\text{ and } %s \\ge 0, \\qquad %s = \\mathrm{NaN} \\text{ otherwise}.$$"
                        % (s, gate, s, gate, s, name_tex(f), name_tex(r), s, when, s, name_tex(r)))
            return ("The result of a fold of maxima from its final state, the largest magnitude $%s$%s: $%s$ when "
                    "%sit is finite, with the flag $%s$ true; otherwise a NaN and the flag false (the canonical NaN "
                    "of [When something is not finite](../developer/design/milestone2.md#sum-dot-axpy-convolution))"
                    ":\n\n$$%s = %s \\ %s, \\qquad %s = \\mathrm{NaN} \\text{ otherwise}.$$" % (
                        name_tex(m), (" and the mask $%s$ that no element was a NaN" % gate) if gate else "", s,
                        ("$%s$ is true and " % gate) if gate else "", name_tex(f), name_tex(r), s, when, name_tex(r)))
        if "finite_or_nan" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "finite_or_nan")
            s, r, f = k.value[1], x["of"], x["flag"]
            return ("The result of a fold from its final state $%s$: the state itself when its leading limb is "
                    "finite, with the flag $%s$ true; otherwise a NaN in every limb and the flag false (the "
                    "canonical NaN of [When something is not finite](../developer/design/milestone2.md#"
                    "sum-dot-axpy-convolution)):\n\n$$%s = %s \\ \\text{when } %s_0 \\text{ is finite}, "
                    "\\qquad %s = \\mathrm{NaN} \\text{ otherwise}.$$" % (
                        name_tex(s), name_tex(f), name_tex(r), name_tex(s), name_tex(s), name_tex(r)))
        if kinds and all(x["kind"] == "upper" and "value" in x for x in e["ensures"]) and \
                any("unless" in x or "exact_when" in x for x in e["ensures"]):
            # The radius of the scaling of a BallVector by a power of two: at least an expression, that
            # expression exactly under conditions (a mask input among them), and at least another when a
            # mask input is false.
            parts, first = [], None
            for x in e["ensures"]:
                r = name_tex(x["of"])
                w = tex(k.expr(x["value"], "upper value", k.names | {"u", "eta"}, constants=True))
                if "unless" in x:
                    parts.append("at least $%s$ when $%s$ is false" % (w, name_tex(x["unless"])))
                elif "exact_when" in x:
                    parts.append("at least $%s$, and exactly that when %s" % (w, k.exact_tex(x["exact_when"])))
                    first = first or "%s \\ge %s" % (r, w)
                else:
                    parts.append("at least $%s$" % w)
                    first = first or "%s \\ge %s" % (r, w)
            return "A number of `T` %s:\n\n$$%s.$$" % ("; ".join(parts), first or r)
        if kinds and all(x["kind"] == "holds" or (x["kind"] == "upper" and "value" in x) for x in e["ensures"]):
            # An exported bound: each output bounds an expression of the inputs, under a mask.
            masks = sorted({x["if"] for x in e["ensures"] if "if" in x})
            bounds = [k.finite_bullet(x)[len("when $%s$ is true, " % name_tex(x["if"])):] if "if" in x
                      else k.finite_bullet(x) for x in e["ensures"] if x["kind"] == "upper"]
            return ("Numbers of `T` that bound expressions of $%s$ from above%s:"
                    "\n\n$$%s.$$" % (", ".join(name_tex(i) for i in k.inputs),
                                       (", valid when the mask %s is true" %
                                        " and ".join("$%s$" % name_tex(m) for m in masks)) if masks else "",
                                       ", \\qquad ".join(b.strip("$") for b in bounds)))
        if "ball_set" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "ball_set")
            (a, _), (b, _) = x["balls"].items()
            op, what = KNOWN_SET_OPERATIONS[x["set"]]
            return ("A ball that contains the %s of two balls, %s; the empty set and the whole line included:\n\n"
                    "$$Z \\supseteq %s %s %s.$$" % ("union" if x["set"] == "union" else "intersection",
                                                    self.ball_definitions(k, x), name_tex(a).upper(), op,
                                                    name_tex(b).upper()))
        if "ball_splits" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "ball_splits")
            c, r = self.center_tex(k, x["from"]["center"]), name_tex(x["from"]["radius"])
            (ca, ra), (cb, rb) = ((self.center_tex(k, q["center"]), name_tex(q["radius"])) for q in x["parts"])
            return ("Two balls that together cover the ball $X$ of center $%s$ and radius $%s$, one each half:\n\n"
                    "$$[%s - %s, %s] \\subseteq [%s - %s, %s + %s], \\qquad [%s, %s + %s] \\subseteq [%s - %s, %s + %s].$$" % (
                        c, r, c, r, c, ca, ra, ca, ra, c, c, r, cb, rb, cb, rb))
        if "certain" in kinds or "trit" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] in ("certain", "trit"))
            sets = self.set_definitions(k, x)
            if x["kind"] == "certain":
                return ("Whether %s, %s; a mask that is true only if it holds:\n\n$$%s \\implies %s.$$" % (
                    self.set_relation(k, x), sets, name_tex(x["of"]), self.set_relation(k, x, formula=True)))
            every = (" for every choice of members", " for every choice") if x["rel"] != "member" else ("", "")
            return ("The three-valued answer to whether %s, %s: *yes* only if it holds%s, *no* only if it fails%s, "
                    "otherwise *unknown*, both masks false:\n\n$$%s \\implies %s, \\qquad %s \\implies %s.$$" % (
                        self.set_relation(k, x), sets, every[0], every[1], name_tex(x["yes"]),
                        self.set_relation(k, x, formula=True), name_tex(x["no"]),
                        self.set_relation(k, x, formula=True, negated=True)))
        if "makes_interval" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "makes_interval")
            lo, hi = name_tex(x["from"]["lower"]), name_tex(x["from"]["upper"])
            return ("The interval of two values of `T`; the whole line when a bound is a NaN or both are the same "
                    "infinity, and the empty set when they are reversed:\n\n$$Z = [%s, %s].$$" % (lo, hi))
        if "interval_set" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "interval_set")
            (a, _), (b, _) = x["intervals"].items()
            op, what = KNOWN_SET_OPERATIONS[x["set"]]
            A, B = name_tex(a).upper(), name_tex(b).upper()
            return ("The %s of two intervals%s, exactly; the empty set included:\n\n$$Z = %s.$$" % (
                what, ", the smallest interval that contains both" if x["set"] == "union" else "",
                ("\\mathrm{hull}(%s \\cup %s)" if x["set"] == "union" else "%s \\cap %s") % (A, B)))
        if "ball_of_interval" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "ball_of_interval")
            lo, hi = name_tex(x["from"]["lower"]), name_tex(x["from"]["upper"])
            c, r = k.out_tex(x["center"]), name_tex(x["radius"])
            if x["special"] == "ieee1788":
                return ("The midpoint $%s$ and the radius $%s$ of the interval $[%s, %s]$, with the values of `mid` "
                        "and `rad` of IEEE 1788 for an unbounded or empty interval:\n\n$$[%s - %s, %s + %s] "
                        "\\supseteq [%s, %s].$$" % (c, r, lo, hi, c, r, c, r, lo, hi))
            return ("A ball of center $%s$ and radius $%s$ that contains the interval $[%s, %s]$: the whole line for "
                    "an unbounded interval, the empty set for the empty one:\n\n$$[%s - %s, %s + %s] \\supseteq "
                    "[%s, %s].$$" % (c, r, lo, hi, c, r, c, r, lo, hi))
        if "interval_of_ball" in kinds and next(x for x in e["ensures"] if x["kind"] == "interval_of_ball")[
                "tight"]["kind"] == "outward":
            x = next(x for x in e["ensures"] if x["kind"] == "interval_of_ball")
            b, cr = next(iter(x["balls"].items()))
            c, r = name_tex(cr["center"]), name_tex(cr["radius"])
            return ("An interval with bounds of two limbs that contains the ball of center $%s$ and radius $%s$, each "
                    "bound within $A\\lvert v\\rvert + B$ of the bound $v$ of the ball:\n\n"
                    "$$Z \\supseteq [%s - %s, %s + %s].$$" % (c, r, c, r, c, r))
        if "interval_of_ball" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "interval_of_ball")
            b, cr = next(iter(x["balls"].items()))
            c, r = name_tex(cr["center"]), name_tex(cr["radius"])
            return ("The smallest interval of `T` that contains the ball of center $%s$ and radius $%s$:\n\n"
                    "$$Z = [\\mathrm{RD}(%s - %s), \\mathrm{RU}(%s + %s)].$$" % (c, r, c, r, c, r))
        if "splits" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "splits")
            lo, hi = name_tex(x["from"]["lower"]), name_tex(x["from"]["upper"])
            (al, au), (bl, bu) = ((name_tex(q["lower"]), name_tex(q["upper"])) for q in x["parts"])
            return ("Two intervals that together are $X = [%s, %s]$, split at a point of it:\n\n$$X = [%s, %s] "
                    "\\cup [%s, %s].$$" % (lo, hi, al, au, bl, bu))
        if "encloses_interval" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "encloses_interval")
            s, each, names = self.interval_set(k, x)
            defs = " and ".join("$%s = [%s, %s]$" % (name_tex(n).upper(), name_tex(b["lower"]), name_tex(b["upper"]))
                                for n, b in x["intervals"].items())
            return ("An interval $Z = [%s, %s]$ that contains $%s$ for every %s, with %s. An interval may be "
                    "unbounded, and empty.\n\n$$Z \\supseteq \\{\\, %s : %s \\,\\}.$$" % (
                        name_tex(x["lower"]), name_tex(x["upper"]), s, each, defs, s,
                        ", ".join("%s \\in %s" % (name_tex(n), name_tex(n).upper()) for n in names)))
        if "set_bound" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "set_bound")
            b, cr = next(iter(x["balls"].items()))
            below = x["side"] == "below"
            return ("A%s bound of the ball $%s$ of center $%s$ and radius $%s$, as a number of `T`:\n\n"
                    "$$%s %s %s \\text{ for every } %s \\in %s.$$" % (
                        " lower" if below else "n upper", name_tex(b).upper(), name_tex(cr["center"]),
                        name_tex(cr["radius"]), name_tex(x["of"]), "\\le" if below else "\\ge", name_tex(b),
                        name_tex(b), name_tex(b).upper()))
        if "makes_ball" in kinds and "lower" in next(x for x in e["ensures"] if x["kind"] == "makes_ball")["from"]:
            x = next(x for x in e["ensures"] if x["kind"] == "makes_ball")
            lo, hi = name_tex(x["from"]["lower"]), name_tex(x["from"]["upper"])
            # Only a claim with midpoint_when (the center of two limbs) says the center is the exact
            # midpoint; a center of one limb is within the bound its page gives of it.
            exact = ", with the exact midpoint for its center when halving is exact" if "midpoint_when" in x else ""
            return ("A ball $Z$, of center $%s$ and radius $%s$, that contains the interval $[%s, %s]$ of two values "
                    "of `T`%s; or the whole line, or the "
                    "empty set:\n\n$$Z \\supseteq [%s, %s].$$" % (
                        name_tex(x["center"]), name_tex(x["radius"]), lo, hi, exact, lo, hi))
        if "outward" in kinds:
            xs = [x for x in e["ensures"] if x["kind"] == "outward"]
            parts = " \\le ".join([k.out_tex(x["of"]) for x in xs if x["side"] == "below"] + [v] +
                                  [k.out_tex(x["of"]) for x in xs if x["side"] == "above"])
            return ("%s of $%s$, of two limbs, within $A\\lvert %s\\rvert + B$ of it:\n\n$$%s.$$" % (
                "Two bounds" if len(xs) > 1 else ("A lower bound" if xs[0]["side"] == "below" else "An upper bound"),
                v, v, parts))
        if "encloses" in kinds and not next(x for x in e["ensures"] if x["kind"] == "encloses")["balls"]:
            x = next(x for x in e["ensures"] if x["kind"] == "encloses")
            return ("An approximation $%s$ of $%s$ with a bound $%s$ of its error:\n\n$$\\lvert %s - %s\\rvert \\le %s.$$" % (
                k.out_tex(x["center"]), v, name_tex(x["radius"]), parenthesized(k.value), k.out_tex(x["center"]),
                name_tex(x["radius"])))
        if "bound" in kinds and len(k.outputs) == 2:
            lo = next(x for x in e["ensures"] if x["kind"] == "bound" and x["side"] == "below")
            hi = next(x for x in e["ensures"] if x["kind"] == "bound" and x["side"] == "above")
            return ("Both directed products of $%s$ from one rounding, a bound below and one above, each within a "
                    "step of its rounding:\n\n$$%s \\le %s \\le %s.$$" % (v, name_tex(lo["of"]), v, name_tex(hi["of"])))
        if "makes_ball" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "makes_ball")
            c, r = name_tex(x["from"]["center"]), name_tex(x["from"]["radius"])
            return ("The ball of center $%s$ and radius $%s$, or the empty set or the whole line when they do "
                    "not make a finite ball:\n\n$$Z = \\{\\, t : \\lvert t - %s\\rvert \\le %s \\,\\}.$$" % (c, r, c, r))
        if "represents" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "represents")
            return "The two-limb number with the value $%s$, exactly:\n\n$$%s = %s.$$" % (v, name_tex(x["of"]), v)
        if "encloses" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "encloses")
            s = tex(k.expr(x["set"], "encloses", set(x["balls"]) | set(k.inputs)))
            over = ", ".join("%s \\in %s" % (name_tex(b), name_tex(b).upper()) for b in x["balls"])
            balls = " and ".join("$%s$ the ball of center $%s$ and radius $%s$" % (
                name_tex(b).upper(), name_tex(cr["center"]), name_tex(cr["radius"])) for b, cr in x["balls"].items())
            special = (" A ball may also be the whole line or the empty set." if k.extended and not k.finite_reading
                       else "")
            return ("A ball $Z$, of center $%s$ and radius $%s$, that contains $%s$ for every $%s$, with %s.%s"
                    "\n\n$$Z \\supseteq \\{\\, %s : %s \\,\\}.$$" % (
                        name_tex(x["center"]), name_tex(x["radius"]), s, over, balls, special, s, over))
        if "predicate" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "predicate")
            rel = k.relation(x)
            return "Whether $%s$, for the exact values:\n\n$$%s = [\\, %s \\,].$$" % (rel, name_tex(x["of"]), rel)
        out = name_tex(k.outputs[0]) if len(k.outputs) == 1 else None
        if "neighbor" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "neighbor")
            step, where = KNOWN_SIDES["neighbor"][x["side"]]
            return "The next number of `T` %s $%s$, for every value of `T`:\n\n$$%s = \\mathrm{%s}(%s).$$" % (
                where, v, out, step, v)
        if "bound" in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "bound")
            below = x["side"] == "below"
            return ("A%s bound of $%s$, a number of `T` within %d step%s of its rounding %s, and that rounding "
                    "itself %s:\n\n$$%s %s %s.$$" % (
                        " lower" if below else "n upper", v, x["steps"], "" if x["steps"] == 1 else "s",
                        KNOWN_SIDES["bound"][x["side"]][1],
                        "where the claims say so (below)" if "rounded" in kinds else "in no case claimed",
                        out, "\\le" if below else "\\ge", v))
        if "rounded" in kinds and len(k.outputs) == 1 and len(k.limbs(k.outputs[0])) == 1 and "error" not in kinds:
            x = next(x for x in e["ensures"] if x["kind"] == "rounded")
            return "$%s$ rounded to a number of `T`:\n\n$$%s = \\mathrm{%s}(%s).$$" % (
                v, out, KNOWN_MODES[x["mode"]], v)
        if "upper" in kinds:
            return "An upper bound of $%s$, a number of `T`:\n\n$$%s \\ge %s.$$" % (v, out, v)
        if "maximum" in kinds:
            # The combination and the steps of a fold of maxima: the larger of two values, and a mask
            # (the and of the masks: that no element was a NaN), which the claims do not describe.
            x = next(x for x in e["ensures"] if x["kind"] == "maximum")
            a, b = (tex(k.limb_expr(y, "maximum")) for y in x["args"])
            masks = [name_tex(o) for o in k.outputs if o != x["of"]]
            return ("The larger of $%s$ and $%s$, exactly, by a comparison%s:\n\n$$%s = \\max(%s, %s).$$" % (
                a, b, ("; and the mask $%s$ of a fold of maxima, true while no element was a NaN, which the claims "
                       "do not describe" % masks[0]) if masks else "", name_tex(x["of"]), a, b))
        own = [x for x in e["ensures"] if x["kind"] == "rounded" and "value" in x]
        if own and len(k.outputs) == 2 and len(own) == 1:
            # The kernels of the accumulator: the running sum, an approximation of the kernel's value
            # (rounded to nearest with one limb), and the sum of the magnitudes, a rounding of a
            # value of its own.
            x = own[0]
            main = next(o for o in k.outputs if o != x["of"])
            w = tex(k.limb_expr(x["value"], "rounded"))
            mine = [y for y in e["ensures"] if y["kind"] == "rounded" and y["of"] == main and "value" not in y]
            first = ("$%s = \\mathrm{%s}(%s)$" % (k.out_tex(main), KNOWN_MODES[mine[0]["mode"]], v) if mine
                     else "$%s \\approx %s$" % (k.out_tex(main), v))
            return ("A step of an accumulator: the running sum %s, and the sum of the magnitudes $%s$ rounded "
                    "to a number of `T`:\n\n$$%s, \\qquad %s = \\mathrm{%s}(%s).$$" % (
                        first, name_tex(x["of"]), first.strip("$"), name_tex(x["of"]), KNOWN_MODES[x["mode"]], w))
        flagged = [x for x in e["ensures"] if x["kind"] == "error" and "exact_flag" in x]
        if flagged and len(k.outputs) == 2:
            # The steps of the scalings of a BallVector by a power of two: an approximation, exact under
            # conditions, and the mask that they hold.
            x = flagged[0]
            return ("An approximation $%s$ of $%s$, exact when %s; and the mask $%s$, true exactly when those "
                    "conditions hold:\n\n$$%s \\approx %s.$$" % (
                        k.out_tex(x["of"]), v, k.exact_tex(x["exact_when"]), name_tex(x["exact_flag"]),
                        k.out_tex(x["of"]), v))
        if len(k.outputs) != 1:
            fail("kernel %s: %d outputs, and no ball or predicate claim: no template" % (k.name, len(k.outputs)))
        out = k.out_tex(k.outputs[0])
        if k.errors and all(k.bound_tex(x) is None for x in k.errors):
            return "$%s$, exactly:\n\n$$%s = %s.$$" % (v, out, v)
        return "An approximation $%s$ of $%s$:\n\n$$%s \\approx %s.$$" % (out, v, out, v)

    def short(self, k):
        """One line for the index."""
        if k.finite_reading:
            return k.finite_short()
        e = k.entry
        parts = []
        for x in e["ensures"]:
            if x["kind"] == "extends":
                parts.append("canonical; the result of %s when finite, $(\\pm\\infty, 0)$ on overflow, as `T` "
                             "for infinite and NaN operands" % self.link(self.core[k.name]))
            elif x["kind"] == "encloses":
                parts.append("a canonical ball that contains every $%s$; the empty set and the whole line "
                             "included" % tex(k.expr(x["set"], "encloses", set(x["balls"]) | set(k.inputs))))
            elif x["kind"] == "represents":
                parts.append("$%s = %s$ exactly, canonical" % (name_tex(x["of"]), tex(k.value)))
            elif x["kind"] == "makes_ball" and "lower" in x["from"]:
                parts.append("a canonical ball that contains $[%s, %s]$; the whole line for a NaN bound and for "
                             "the same infinity twice" % (
                    name_tex(x["from"]["lower"]), name_tex(x["from"]["upper"])))
            elif x["kind"] == "makes_ball":
                parts.append("the ball of center $%s$ and radius $%s$, canonical" % (
                    name_tex(x["from"]["center"]), name_tex(x["from"]["radius"])))
            elif x["kind"] == "finite_or_nan":
                parts.append("$%s$ when its leading limb is finite, flag true; otherwise NaN, flag false" % (
                    tex(k.value)))
            elif x["kind"] == "makes_interval":
                parts.append("the interval $[%s, %s]$, canonical; the whole line for a NaN bound and for the "
                             "same infinity twice" % (
                    name_tex(x["from"]["lower"]), name_tex(x["from"]["upper"])))
            elif x["kind"] == "encloses_interval":
                s, _, _ = self.interval_set(k, x)
                parts.append("a canonical interval that contains every $%s$; %s" % (s, {
                    "exact": "exactly the range", "rounded": "the range rounded outward" + (
                        ", within a step" if x["tight"].get("steps") else ""),
                    "outward": "within $A\\lvert v\\rvert + B$ of the range"}[x["tight"]["kind"]]))
            elif x["kind"] == "set_bound":
                parts.append("a %s bound of the ball%s; $%s\\infty$ for the empty ball" % (
                    "lower" if x["side"] == "below" else "upper", ", rounded" if x.get("tight") else "",
                    "+" if x["side"] == "below" else "-"))
            elif x["kind"] == "error":
                parts.append(k.finite_bullet(x, short=True))
            elif x["kind"] == "normalized":
                parts.append("$%s$ canonical, normalized when finite" % name_tex(x["of"]))
            elif x["kind"] == "outward":
                parts.append("a %s bound of $%s$, within $A\\lvert v\\rvert + B$ when finite%s" % (
                    "lower" if x["side"] == "below" else "upper", tex(k.value),
                    "; zero for a zero operand" if x.get("zero_factor") else ""))
            elif x["kind"] == "interval_set":
                parts.append("the %s of the intervals, exactly" % KNOWN_SET_OPERATIONS[x["set"]][1])
            elif x["kind"] == "ball_of_interval":
                parts.append("the midpoint and radius, the values of IEEE 1788 when unbounded or empty"
                             if x["special"] == "ieee1788" else
                             "a canonical ball that contains the interval; the whole line when it is unbounded")
            elif x["kind"] == "interval_of_ball" and x["tight"]["kind"] == "outward":
                parts.append("an interval of two limbs that contains the ball, within $A\\lvert v\\rvert + B$ of its "
                             "bounds; empty for the empty ball")
            elif x["kind"] == "interval_of_ball":
                parts.append("the smallest interval of `T` that contains the ball; empty for the empty ball")
            elif x["kind"] == "splits":
                parts.append("two intervals that together are the operand, split at a point of it")
            elif x["kind"] == "certain":
                parts.append("whether $%s$; %s" % (self.set_relation(k, x, formula=True),
                                                   "exact" if x.get("exact") else "true only if it holds"))
            elif x["kind"] == "ball_set":
                parts.append("a canonical ball Z that contains the %s of the balls; when X is empty, Z is Y as it is "
                             "(the same limbs); when Y is empty and X is not, Z is X as it is" % x["set"]
                             if x["set"] == "union" else
                             "a canonical ball Z that contains the intersection of the balls; when X is the whole line, "
                             "Z is Y as it is (the same limbs); when Y is the whole line and X is not, Z is X as it is")
            elif x["kind"] == "ball_splits":
                parts.append("two canonical balls that cover the two halves of the ball")
            elif x["kind"] == "trit":
                parts.append("yes, no or unknown: whether $%s$; %s" % (
                    self.set_relation(k, x, formula=True), "exact" if x.get("exact") else "never wrong"))
            else:
                fail("kernel %s: no index line for the claim kind %r" % (k.name, x["kind"]))
        return "; ".join(parts)

    def constants(self, k):
        out = []
        w = out.append
        proved = k.proved
        w("The constants of the bound%s, for each limb type, from `gen/claims.json`%s:" % (
            "" if proved else " (a target, not a guarantee)",
            "; `kairn::traits` exports them rounded up to `T`" if proved and self.ops.KERNELS[k.name]["traits"] else ""))
        w("")
        w("| | %s |" % " | ".join("`%s`" % ctype for _, ctype, _, _ in FORMATS))
        w("|---|" + "---|" * len(FORMATS))
        w("| unit roundoff $u$ | %s |" % " | ".join("$2^{-%d}$" % p for _, _, p, _ in FORMATS))
        for i, x in enumerate(k.errors):
            cond = " (%s)" % k.when_tex(x) if x["when"] else ""
            if parse(x["c"], "kernel %s, c" % k.name, {"u"}) != ("num", 0):
                w("| relative term $c\\,u%s$%s | %s |" % ("" if x["k"] == 1 else "^%s" % x["k"], cond, " | ".join(
                    constant_tex(k.entry["instances"][fmt][i]["rel"]) for fmt, _, _, _ in FORMATS)))
            if fractions.Fraction(x["t"]) != 0:
                w("| absolute term $t\\,\\eta$%s | %s |" % (cond, " | ".join(
                    constant_tex(k.entry["instances"][fmt][i]["abs"]) for fmt, _, _, _ in FORMATS)))
        exported = [(ctype, self.bounds.get((k.name, ctype), {})) for _, ctype, _, _ in FORMATS]
        if proved and all("unit" in b for _, b in exported):
            w("| `unit`, `tiny`, as compiled | %s |" % " | ".join(
                "`%s`, `%s`" % (b["unit"], b["tiny"]) for _, b in exported))
            if all("unit_computed" in b for _, b in exported):
                w("| `unit_computed`, `tiny_computed` | %s |" % " | ".join(
                    "`%s`, `%s`" % (b["unit_computed"], b["tiny_computed"]) for _, b in exported))
        w("")
        traits = self.ops.KERNELS[k.name]["traits"]
        if proved and traits:
            groups = {}
            for t in traits:
                owner, member = t.split("::")
                groups.setdefault(owner, []).append(member)
            names = []
            for owner, members in groups.items():
                text = "the entr%s %s of `kairn::%s`" % ("y" if len(members) == 1 else "ies",
                                                      ", ".join("`%s`" % m for m in members), owner)
                if owner == "traits<T>":
                    text += " (`T` is `float` or `double`; `kairn::traits<Expansion<T, 1>>` is the same)"
                names.append(text)
            shared = []
            for t in traits:
                others = [n for n, q in self.ops.KERNELS.items() if n != k.name and t in q["traits"]]
                if others:
                    shared.append("`%s` holds the larger constants of %s" % (
                        t.split("::")[1], " and ".join(self.link(n) for n in [k.name] + others)))
            forms = {x["form"] for x in k.errors if not x["when"]}
            if forms == {"R"}:
                meaning = ("`unit` and `tiny` bound the error relative to the exact result, `unit_computed` "
                           "and `tiny_computed` relative to the computed one ($\\lvert \\text{error}\\rvert \\le "
                           "\\mathtt{unit\\_computed}\\,\\lvert\\text{computed}\\rvert + \\mathtt{tiny\\_computed}$)")
            elif forms == {"A"}:
                meaning = ("`unit` and `tiny` bound the error relative to the sum of the magnitudes of the "
                           "operands (`reference` is `BoundForm::operands`); no bound relative to the computed "
                           "value follows, and `unit_computed` and `tiny_computed` are $+\\infty$")
            elif forms == {"T"}:
                meaning = ("`unit` and `tiny` bound the error relative to the sum of the magnitudes of the "
                           "terms of the exact value ($\\lvert a x\\rvert + \\lvert y\\rvert$ for $a x + y$; "
                           "`reference` is `BoundForm::terms`); no bound relative to the computed value follows, "
                           "and `unit_computed` and `tiny_computed` are $+\\infty$")
            else:
                fail("kernel %s: its unconditional error claims have the forms %s, which the constants "
                     "sentence has no template for" % (k.name, sorted(forms)))
            w("The compiled constants are %s: %s%s." % (
                "; ".join(names), meaning, "; " + "; ".join(shared) if shared else ""))
            w("")
        return "\n".join(out)

    def ball_constants(self, k, users):
        rows = []
        for u in users:
            vals = []
            for _, ctype, _, _ in FORMATS:
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

    def precision(self, k, extended):
        mp = k.entry["min_precision"]
        if mp is None:
            return ("The smallest precision for which the statement holds is not known yet; the oracle "
                    "judges every format.")
        if not isinstance(mp, int):
            fail("kernel %s: min_precision %r is not an integer" % (k.name, mp))
        proved = k.ieee_proved if extended else k.proved
        short = [ctype for _, ctype, p, _ in FORMATS if p < mp]
        types = ", ".join("`%s` has %d bits" % (ctype, p) for _, ctype, p, _ in FORMATS)
        model = ("in the IEEE model, with signed zeros, infinities, NaN and overflow" if extended
                 else "in the model where no operation overflows")
        return ("%s for every binary format with a precision of at least %d bit%s, rounding to nearest with "
                "ties to even and with gradual underflow, %s. %s" % (
                    "Proved" if proved else "Stated", mp, "" if mp == 1 else "s", model,
                    "**Not covered: %s** (%s)." % (", ".join("`%s`" % c for c in short), types) if short
                    else "Both limb types qualify: %s." % types))

    def theorem_text(self, k, th, field, statement):
        if not th or not th.get("file") or not th.get("name"):
            fail("kernel %s: a proved statement names no theorem (%s)" % (k.name, field))
        path = os.path.join(self.root, th["file"])
        if not os.path.exists(path):
            fail("kernel %s: its theorem file %s does not exist" % (k.name, th["file"]))
        if not re.search(r"\b(Theorem|Lemma)\s+%s\b" % re.escape(th["name"]), read(path)):
            fail("kernel %s: %s has no theorem %s" % (k.name, th["file"], th["name"]))
        audit = self.audited.get(th["name"])
        if audit is None:
            fail("kernel %s: no audit file prints the assumptions of its theorem %s (%s)"
                 % (k.name, th["name"], ", ".join(AUDIT_FILES)))
        return ("**Proved.** Rocq checks the theorem `%s`, in [`%s`](%s/blob/main/%s)%s; the audit of "
                "`make -C proofs` prints the axioms its proof depends on (`Print Assumptions %s`, in "
                "[`%s`](%s/blob/main/%s)) and finds none beyond the %s allowed ([Axioms](#axioms))." % (
                    th["name"], th["file"], REPO_URL, th["file"], statement, th["name"], audit, REPO_URL, audit,
                    self.axiom_count()))

    def axiom_count(self):
        n = len(self.allowed_axioms)
        return NUMBER_WORDS.get(n, str(n))

    def proved_theorems(self, k):
        """The theorems the page calls proved, in the order it names them."""
        names = []
        if k.proved:
            th = k.entry.get("theorem") if k.finite_reading else (k.entry.get("ieee_theorem") or k.entry.get("theorem"))
            names.append(th["name"])
        if k.extended and k.finite_reading and k.ieee_proved:
            names.append(k.entry["ieee_theorem"]["name"])
        return names

    def axioms(self, k):
        """The section on the axioms of the page's proved theorems, or None if it has none."""
        names = self.proved_theorems(k)
        if not names:
            return None
        whose = ("the proof of `%s` depends on" % names[0] if len(names) == 1 else
                 "the proofs of %s depend on" % " and ".join("`%s`" % n for n in names))
        out = ["The audit accepts a proof only if every axiom it depends on is one of the %s listed in "
               "[`%s`](%s/blob/main/%s) ([Proofs](../proofs/index.md#the-four-axioms) says what each states):"
               % (self.axiom_count(), ALLOWED_AXIOMS, REPO_URL, ALLOWED_AXIOMS), ""]
        out.extend("- `%s`" % a for a in self.allowed_axioms)
        out.append("")
        out.append("Which of them %s is not copied here: only a run of Rocq computes it. The CI prints it for "
                   "every push to `main` and every pull request, and keeps what the audit printed as the artifact "
                   "`%s` of each run of the [Proofs workflow](%s)." % (whose, AUDIT_ARTIFACT, PROOFS_WORKFLOW))
        return "\n".join(out)

    def status(self, k):
        e = k.entry
        spec = self.statements.get(k.name)
        if k.finite_reading and spec is None:
            fail("kernel %s: proofs/gen/Statements.v has no %s_spec; run python3 gen/kairn-gen build"
                 % (k.name, k.name))
        if k.proved:
            th = e.get("theorem") if k.finite_reading else (e.get("ieee_theorem") or e.get("theorem"))
            text = self.theorem_text(k, th, "theorem", (
                ", against `%s_spec`, the statement the generator prints from these claims into "
                "[`proofs/gen/Statements.v`](%s/blob/main/proofs/gen/Statements.v)" % (k.name, REPO_URL))
                if spec is not None else "")
        else:
            text = "**UNVERIFIED.** No proof of the statement is checked."
            th = e.get("theorem")
            if th and th.get("file") and th.get("name"):
                text += " The theorem is to be `%s`, in `%s`." % (th["name"], th["file"])
            if k.extended and not k.finite_reading:
                text += " " + IEEE_PROOFS_SENTENCE
        if spec is None:
            return text
        return (text + "\n\nThe statement, as Rocq reads it (the vocabulary, `fmt`, `RN`, `u`, `eta` and "
                "`normalized_2`, is defined at the top of the same file; `emin` is the exponent of $\\eta$ "
                "and `prec` the precision):\n\n```coq\n%s\n```" % spec)

    def ieee_status(self, k):
        if k.ieee_proved:
            return "**Status of this statement:** " + self.theorem_text(
                k, k.entry.get("ieee_theorem"), "ieee_theorem", "").replace("**Proved.**", "proved.", 1)
        return ("**Status of this statement: UNVERIFIED.** No proof of it is checked (`ieee_status` is "
                "`unverified` in `gen/claims.json`). " + IEEE_PROOFS_SENTENCE)

    def cite(self, text):
        refs = os.path.join(self.root, "docs", "developer", "design", "phase0", "references.md")
        anchors = set(re.findall(r'<a id="([^"]+)"', read(refs))) if os.path.exists(refs) else set()

        def sub(m):
            key = m.group(0)
            if key.lower() in anchors:
                return "[%s](../developer/design/phase0/references.md#%s)" % (key, key.lower())
            return key
        return re.sub(r"\b[A-Z]{2,}\d{2}\b", sub, text)

    def not_claimed(self, k):
        lines = []
        if k.finite_reading and not k.extended:
            full = self.full_of.get(k.name, [])
            if full:
                pending = all(self.not_called(f) for f in full)
                lines.append("Anything when an operand is infinite or NaN, or when an operation of the kernel "
                             "overflows: %s states that%s "
                             "([What holds today](../getting-started/guarantees.md#overflow-and-non-finite-values) "
                             "says what the library does now)." % (
                                 " and ".join(self.link(f) for f in full),
                                 (", and the public headers do not call %s yet" % ("them" if len(full) > 1 else "it"))
                                 if pending else ""))
            else:
                lines.append("Anything when an operand is infinite or NaN, or when an operation of the kernel "
                             "overflows: what is proved and what is not written yet there is in "
                             "[What holds today](../getting-started/guarantees.md#overflow-and-non-finite-values).")
        if k.extended:
            lines.append("Anything for operands that do not satisfy the requirements%s." % (
                " of the statement on infinite and NaN operands" if k.finite_reading else ""))
            kinds = [x["kind"] for x in k.entry["ensures"]]
            if any(x in ("normalized", "error") for x in kinds) and "represents" not in kinds:
                lines.append("Which canonical value comes out when an operand is not finite: the claims say only "
                             "that it is canonical.")
            lines.append("The sign of a zero limb, and which NaN a NaN result is: the claims compare neither.")
        if k.finite_reading and any(r in ("normalized", "canonical") or (r == "ball" and len(k.limbs(a[0])) == 2)
                                    for r, a in k.requires):
            lines.append("Anything about an operand that is not normalized, which only limbs given by the program "
                         "can make: `from_limbs` in a build without checks, `from_limbs_unchecked`, or `limb[]` "
                         "written directly.")
        if not k.proved:
            lines.append("Anything at all, as a guarantee: the statement is a target until its proof is checked.")
        elif k.extended and not k.ieee_proved:
            lines.append("Anything about infinite and NaN operands, as a guarantee: that statement is a target until "
                         "its proof is checked.")
        return lines

    def campaign_title(self, c):
        m = re.fullmatch(r"milestone(\d+)", c["name"])
        return "Milestone %s" % m.group(1) if m else "`%s`" % c["name"]

    def measured(self, k):
        """The section Measured: the stored brute-force runs whose code is the kernel's now,
        campaign by campaign (results/NAME/brute/, oldest first), and their total when there are
        several; the runs of other code are named and not counted."""
        out = []
        w = out.append
        shown, other = [], []
        for c in self.brute:
            judged = [d for d in c["docs"] + c["supplementary"] if judged_by(d, k.name)]
            same = [d for d in judged if self.same_code(d, k.name)]
            if len(same) < len(judged):
                other.append((c, short_commits(d for d in judged if not any(d is s for s in same))))
            b = brute_of(k.name, c, same, lambda d: self.same_claims(d, k.name)) if same else None
            if b is not None:
                shown.append((c, b))
        not_counted = " and ".join("of %s, at commit%s %s," % (
            self.campaign_title(c), "s" if len(commits) > 1 else "", " and ".join("`%s`" % x for x in commits))
            for c, commits in other)
        if not shown:
            if other:
                w("No stored brute-force run is of this kernel's code as it is now: the runs %s were of other "
                  "code, and are not counted." % not_counted)
            else:
                w("No stored brute-force run has judged this kernel yet.")
            w("")
            return "\n".join(out)
        w("The stored brute-force runs of this kernel's code: the oracle judged, in exact arithmetic, the results "
          "of the compiled kernel (every compiler, scalar and packed code, every contraction setting) on random "
          "operands of `binary64` and `binary32`, and those of the generator's interpreter on every operand of "
          "small formats. A measurement, not a bound. A run is shown only if it ran the code the kernel has now: "
          "its generated C++ (scalar and packed, every kernel it calls inlined, with the functions it calls; "
          "comments left out) must be the same at the commit of the run, as the fingerprints in "
          "[`%s`](%s/blob/main/%s) show ([How to read a page](reading.md#what-the-measured-numbers-are))." % (
              BRUTE_CODE.MANIFEST, REPO_URL, BRUTE_CODE.MANIFEST))
        w("")
        slack = False
        for c, b in shown:
            lines, cols = self.campaign(k, c, b)
            out.extend(lines)
            slack = slack or any(col[2] == "slack" for col in cols)
        if len(shown) > 1:
            out.extend(self.brute_total(k, shown))
        if other:
            w("The runs %s were of other code, and are not counted." % not_counted)
            w("")
        if slack:
            w("The slack is how far the returned radius is above the smallest radius that encloses the "
              "exact set, in units in the last place of the radius: below 1, a radius one unit smaller "
              "would not enclose it.")
            w("")
        return "\n".join(out)

    def brute_total(self, k, shown):
        """The total of the runs of several campaigns, per format, but for the rows that judged
        other claims. The random cases of the compiled runs add up; an enumeration of a domain that
        an earlier one enumerated judged the same operands again, so each domain counts once, by
        its latest complete enumeration."""
        out = []
        w = out.append
        total, left_out = {}, False
        for c, b in shown:
            for r in b["rows"]:
                if not r["same_claims"]:
                    left_out = True
                    continue
                t = total.setdefault(r["key"], {"judged": 0, "failed": 0, "ok": True, "campaigns": [],
                                                "domains": {}})
                t["failed"] += r["failed"] + r["invalid"]
                t["ok"] = t["ok"] and r["ok"]
                if r["key"] == "toy":
                    for e in r["enumerations"]:
                        kept = t["domains"].get(e["domain"])
                        if kept is None or e["complete"] or not kept["complete"]:
                            t["domains"][e["domain"]] = e
                else:
                    t["judged"] += r["judged"]
                if c["name"] not in t["campaigns"]:
                    t["campaigns"].append(c["name"])
        if not total:
            return out
        titles = {c["name"]: self.campaign_title(c) for c, _ in shown}
        w("**In all**, the runs above%s:" % (
            ", but for the rows that judged other claims, which are not counted" if left_out else ""))
        w("")
        w("| Run | Cases judged | Failed |")
        w("|---|---|---|")
        for key, title in [(fmt, "`%s` (`%s`), compiled" % (fmt, ctype)) for fmt, ctype, _, _ in FORMATS] + [
                ("toy", "toy formats")]:
            t = total.get(key)
            if t is None:
                continue
            if key == "toy":
                domains = list(t["domains"].values())
                t["judged"] = sum(e["judged"] for e in domains)
                title += ", every operand of %d distinct domain%s, each counted once" % (
                    len(domains), "s" if len(domains) > 1 else "")
                stopped = sum(not e["complete"] for e in domains)
                if stopped:
                    title += " (%d stopped before the end)" % stopped
            title += ", %s" % " and ".join(titles[n] for n in t["campaigns"])
            if not t["ok"]:
                title += " (**a guard failed**)"
            w("| %s | %s | %s |" % (title, fmt_int(t["judged"]), fmt_int(t["failed"])))
        w("")
        return out

    def other_claims_note(self, k, b):
        """The note on the runs of a campaign that judged other claims than the kernel's now, which
        the fingerprints of the claims of the commit each run names decide (results/brute-code.json):
        nothing when every run judged the claims now; otherwise what they judged, by the oracle's
        labels, and whether that is every row or the rows marked "other claims"."""
        other = [r for r in b["rows"] if not r["same_claims"]]
        if not other:
            return []
        commits = lambda cs: "commit%s %s" % ("s" if len(cs) > 1 else "", " and ".join("`%s`" % x for x in cs))
        then = next((r["entries"] for r in other if r["entries"]), None)
        if k.extended and b["extended"]:
            now = [k.label(e) for e in k.entry["ensures"]]
            shown = [x["label"] for x in then[:len(now)]] if then else None
        else:
            now = [k.label(x) for x in (k.finite_entries if k.finite_reading else k.entry["ensures"])]
            shown = [x["label"] for x in then] if then else None
        if shown is None or shown == now:
            # The claims differ where the oracle's labels do not show it.
            judged = ("the claims of %s, which differ from the claims now in what their labels do not show: "
                      "the requirements, the inputs and outputs, the smallest precision or the constants per "
                      "format" % commits(b["other"]))
        else:
            judged = "; ".join("`%s`" % x["label"] for x in then)
        now = "; ".join("`%s`" % x for x in now)
        # A condition finite_when (B4: finite operands under it give a finite ball) that the claims
        # gained after a run: the oracle labels an entry without one "finite when nothing".
        b4 = then is not None and k.extended and b["extended"] and any(
            e.get("finite_when") and "finite when nothing" in x["label"] for x, e in zip(then, k.entry["ensures"]))
        if len(other) == len(b["rows"]):
            text = ("**These runs judged other claims.** They judged %s; the kernel now claims %s. Their numbers "
                    "are not about the statement above." % (judged, now))
        elif b4:
            text = ("**The condition of this claim was not judged by every run.** The claims gained it (B4: finite "
                    "operands under the condition give a finite ball) after the runs of %s, which judged the kernel "
                    "without it, with no condition claimed (the rows marked other claims); the runs of %s judged "
                    "it, on the cases of their rows below." % (commits(b["other"]), commits(b["same"])))
        else:
            text = ("**Not every run below judged the claims above.** The rows marked other claims are of the runs "
                    "of %s, which judged %s; the kernel now claims %s. Their numbers are not about the statement "
                    "above." % (commits(b["other"]), judged, now))
        return [text, ""]

    def campaign(self, k, c, b):
        """The lines of one campaign's runs of the kernel's code, and the columns of its table."""
        out = []
        w = out.append
        page = "docs/developer/results/brute-%s.md" % c["name"]
        where = "the stored summaries in [`%s/`](%s/tree/main/%s)" % (c["dir"], REPO_URL, c["dir"])
        if os.path.exists(os.path.join(self.root, page)):
            where += " ([the report](../developer/results/brute-%s.md#%s))" % (c["name"], k.name)
        main, sup = b["main"], b["supplementary"]
        commits = lambda cs: "commit%s %s" % ("s" if len(cs) > 1 else "", " and ".join("`%s`" % x for x in cs))
        if main and sup:
            runs = "the runs of %s and the supplementary run%s of %s" % (
                commits(main), "s" if len(sup) > 1 else "", "the same commit" if sup == main else commits(sup))
        elif main:
            runs = "the runs of %s" % commits(main)
        else:
            runs = "the supplementary run%s of %s" % ("s" if len(sup) > 1 else "", commits(sup))
        w("**%s**: %s, from %s." % (self.campaign_title(c), runs, where))
        rows = b["rows"]
        # The oracle's entries of the runs that judged the claims now, if any did: the columns.
        judged_labels = next((r["entries"] for r in sorted(rows, key=lambda r: not r["same_claims"])
                              if r["entries"]), None)
        if k.extended and b["extended"]:
            cores = sorted({m.group(1) for x in judged_labels or []
                            for m in [re.match(r"^F2, core (\w+): ", x["label"])] if m})
            w("They judged the kernel in the extended domain, infinite and NaN operands included, as the oracle "
              "reads its statement in the IEEE model ([Claims of the non-finite layer]"
              "(../developer/architecture.md#claims-of-the-non-finite-layer))%s." % (
                  "" if not cores else ", and the claims of its finite core %s on the cases where they apply "
                  "(F2: finite operands, finite result), which the columns below measure"
                  % ", ".join("`%s`" % c for c in cores)))
        elif k.extended:
            w("They judged the statement on finite operands; the stored summaries hold no measurement of the "
              "statement on infinite and NaN operands.")
        w("")
        out.extend(self.other_claims_note(k, b))
        cols = []
        if k.extended and b["extended"]:
            # The oracle's entries: the kernel's own, in the order of its claims, then those of the core
            # of an `extends` entry, labelled "F2, core K: ..." (oracle/kairn_oracle/extended.py).
            n_err = sum(x["kind"] == "error" for x in judged_labels or [])
            for j, x in enumerate(judged_labels or []):
                core = re.match(r"^F2, core (\w+): ", x["label"])
                if x["kind"] == "error":
                    exact = re.search(r"\bc=0, k=\d+, t=0\b", x["label"]) is not None
                    cols.append((j, "largest error / bound" + (" (core `%s`)" % core.group(1) if core and n_err == 1
                                                              else " (%s)" % x["label"] if n_err > 1 else ""),
                                 "exact" if exact else "ratio"))
                elif x["kind"] == "upper":
                    cols.append((j, "largest excess, in gaps", "ratio"))
                elif x["kind"] == "encloses":
                    cols.append((j, "smallest slack of the radius, in gaps", "slack"))
        else:
            # The runs judged the statement on finite operands where there is one: its entries.
            judged = k.finite_entries if k.finite_reading else k.entry["ensures"]
            for j, x in enumerate(judged):
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
        for key, f in b["findings"]:
            w("A finding of the run on %s, %s `%s`: %s." % (
                key[0], {"interp": "the interpreter on"}.get(f.get("part"), f.get("part", "?")),
                f.get("format", "?"), "; ".join(f.get("why", []))))
            w("")
        return out, cols

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
        w("Every public operation of Kairn, grouped by what it does, with the kernel that computes it, and "
          "the kernels that the public headers do not call yet. Each kernel has a page: its statement in "
          "plain mathematics, the C++ forms that reach it, what it requires, what is proved and with which "
          "theorem, its listing, and what the stored brute-force runs of its code measured. "
          "[How to read a page](reading.md) explains each part.")
        w("")
        w("The [C++ API](../%s), which Doxygen generates from the comments of the public headers, lists every "
          "class, function and macro of `include/kairn/*.hpp` with its declaration and its comment; the comment of "
          "an operation names the kernel it calls." % API_PAGE)
        w("")
        if unverified:
            w("Of the %d kernels, %d are proved and %d are **UNVERIFIED**: %s." % (
                len(self.kernels), len(proved), len(unverified), ", ".join(self.link(n) for n in unverified)))
        else:
            w("All %d kernels are proved." % len(self.kernels))
        both = sorted(n for n, k in self.kernels.items() if k.extended and k.finite_reading)
        if both:
            ieee_open = [n for n in both if not self.kernels[n].ieee_proved]
            w("")
            w("%d kernels have a statement on finite operands and one on infinite and NaN operands; the second "
              "is %s." % (len(both), "proved for all of them" if not ieee_open else (
                  "**UNVERIFIED** for all of them" if len(ieee_open) == len(both) else
                  "**UNVERIFIED** for %s" % ", ".join(self.link(n) for n in ieee_open))))
        marked = sorted(n for n in unverified if self.ops.KERNELS[n]["forms"])
        w("")
        if marked:
            w("The operations that call an UNVERIFIED kernel need the marker `kairn::unverified` on an operand: "
              "those of %s." % ", ".join(self.link(n) for n in marked))
        else:
            w("No public operation calls an UNVERIFIED kernel, so none needs the marker `kairn::unverified`.")
        w("")
        w("Notation: $u = 2^{-p}$ is the unit roundoff of the limb type `T` ($2^{-53}$ for `double`, "
          "$2^{-24}$ for `float`), $\\eta$ its smallest positive number, $\\mathrm{RN}$ rounding to nearest "
          "with ties to even, and a two-limb number $x = x_0 + x_1$ is *normalized* when "
          "$x_0 = \\mathrm{RN}(x_0 + x_1)$ ([Numbers](../developer/design/phase0/numbers.md#notation)). "
          "An operand of type `Expansion<T, 1>` next to an `Expansion<T, 2>` is its limb: the form with a "
          "limb of type `T` applies.")
        w("")
        for gid, title, about in self.groups:
            rows = []
            for name, p in self.ops.KERNELS.items():
                k = self.kernels[name]
                forms = [f for f in p["forms"] if (f["group"] or p["group"]) == gid]
                if not forms and not (p["group"] == gid and not p["forms"]):
                    continue
                codes = []
                for f in forms:
                    if f["code"] not in codes:
                        codes.append(f["code"])
                if codes:
                    ops = ", ".join("`%s`" % c for c in codes)
                elif self.not_called(name):
                    ops = NOT_CALLED
                elif name in self.loops_of:
                    ops = "none of its own (in the loop%s %s)" % (
                        "s" if len(self.loops_of[name]) > 1 else "",
                        ", ".join("`%s`" % l for l in self.loops_of[name]))
                else:
                    ops = "none (internal)"
                operands = operand_types(forms[0]) if forms else "-"
                status = "" if k.proved else " **UNVERIFIED**"
                rows.append("| %s | %s | %s | %s%s |" % (ops, operands, self.short(k), self.link(name), status))
            for x in self.ops.EXACT:
                if x["group"] != gid:
                    continue
                for f in x["forms"]:
                    rows.append("| `%s` | %s | %s | %s |" % (f["code"], operand_types(f), x["does"],
                                                             x.get("kernel", "none")))
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
        return "\n".join(out)

    def nav(self):
        lines = [NAV_BEGIN, "  - Reference:", "      - reference/index.md", "      - How to read a page: reference/reading.md",
                 "      - C++ API: %s" % API_PAGE]
        for gid, title, _ in self.groups:
            names = [n for n, p in self.ops.KERNELS.items() if p["group"] == gid]
            pages = [(t, f) for g, t, f in getattr(self.ops, "PAGES", []) if g == gid]
            if not names and not pages:
                continue
            lines.append("      - %s:" % yaml_str(title))
            for n in names:
                lines.append("          - %s: reference/%s.md" % (yaml_str(self.ops.KERNELS[n]["title"]), n))
            for t, f in pages:
                lines.append("          - %s: reference/%s.md" % (yaml_str(t), f))
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


def plan(root, claims=None):
    """{relative path: content} of every file the script owns, mkdocs.yml included."""
    site = Site(root, claims)
    files = site.files()
    mk = os.path.join(root, "mkdocs.yml")
    files["mkdocs.yml"] = with_nav(read(mk), site.nav())
    return files


def hand_written(root):
    """The pages of docs/reference/ written by hand: HAND_WRITTEN and those of PAGES."""
    return HAND_WRITTEN | {f + ".md" for _, _, f in getattr(load_operations(root), "PAGES", [])}


def stray(root, files):
    d = in_root(root, OUT_DIR)
    if not os.path.isdir(d):
        return []
    owned = {p.rsplit("/", 1)[1] for p in files if p.startswith(OUT_DIR + "/")}
    kept = hand_written(root)
    return sorted(OUT_DIR + "/" + f for f in os.listdir(d)
                  if f.endswith(".md") and f not in owned and f not in kept)


def check(root, claims=None):
    """The differences between the committed files and what would be written, as messages."""
    files = plan(root, claims)
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


def write(root):
    files = plan(root)
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
    ap.add_argument("--claims", metavar="PATH",
                    help="read the claims from PATH instead of gen/claims.json, render every page in memory "
                         "and write nothing (with --check, compare with the committed pages instead)")
    a = ap.parse_args(argv)
    try:
        if a.claims and not a.check:
            files = plan(ROOT, a.claims)
            print("reference.py: rendered %d files from %s; nothing written" % (len(files), a.claims))
            return 0
        if a.check:
            problems = check(ROOT, a.claims)
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
