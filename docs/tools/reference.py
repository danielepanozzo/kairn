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
- results/*/brute/*.json: the stored summaries of the latest brute-force runs;
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
HAND_WRITTEN = {"reading.md"}          # pages of docs/reference/ that this script does not own
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

# The fields of each kind of `ensures` entry: required, optional.
KIND_FIELDS = {
    "normalized": ({"of"}, set()),
    "error": ({"of", "form", "c", "k", "t", "when"}, set()),
    "leading_rounded": ({"of"}, set()),
    "rounded": ({"of", "mode"}, set()),
    "upper": ({"of", "gaps"}, set()),
    "predicate": ({"of", "rel", "args"}, set()),
    "encloses": ({"center", "radius", "set", "balls"}, {"finite_when"}),
    "extends": ({"of", "core", "lead", "finite_when"}, set()),
    "represents": ({"of"}, set()),
    "makes_ball": ({"center", "radius", "from"}, set()),
}
# Which kinds and requirements each domain has a reading of.
DOMAIN_KINDS = {
    "finite": {"normalized", "error", "leading_rounded", "rounded", "upper", "predicate", "encloses"},
    "extended": {"normalized", "error", "rounded", "upper", "predicate", "encloses", "extends",
                 "represents", "makes_ball"},
}
DOMAIN_REQUIRES = {
    "finite": {"normalized", "abs_ge", "nonneg", "power_of_two"},
    "extended": {"canonical", "ball", "nonneg", "power_of_two"},
}
# The kinds that exist only for a kernel without a statement on finite operands (a full kernel, a
# constructor), which the claims mark "ieee_only": true; represents too, when it is the only entry.
IEEE_ONLY_KINDS = {"extends", "makes_ball"}

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


def substitute(node, mapping):
    """The tree with each name in mapping replaced by the name it maps to."""
    if node[0] == "name":
        return ("name", mapping.get(node[1], node[1]))
    if node[0] == "num":
        return node
    return (node[0],) + tuple(substitute(n, mapping) for n in node[1:])


def has_product(node):
    if node[0] == "*":
        return True
    return any(isinstance(n, tuple) and has_product(n) for n in node[1:])


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


def natural_key(text):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", text)]


def load_brute(root):
    """The summaries of the latest brute-force runs: those under results/NAME/brute/ with the
    last NAME in natural order (milestone2 after milestone1, milestone10 after milestone2), and
    those of its supplementary runs, under results/NAME/brute/supplementary/: runs of a few
    kernels at a later commit, whose rows a page shows apart."""
    base = os.path.join(root, "results")
    dirs = sorted((d for d in (os.listdir(base) if os.path.isdir(base) else [])
                   if os.path.isdir(os.path.join(base, d, "brute"))), key=natural_key)

    def summaries(rel):
        path = os.path.join(base, rel)
        out = []
        for f in sorted(f for f in (os.listdir(path) if os.path.isdir(path) else []) if f.endswith(".json")):
            data = json.loads(read(os.path.join(path, f)))
            if data.get("kairn_brute_summary") != 1:
                fail("results/%s/%s is not a brute-force summary of version 1" % (rel, f))
            out.append(data)
        return out
    for d in reversed(dirs):
        docs = summaries(os.path.join(d, "brute"))
        if docs:
            return {"name": d, "dir": "results/%s/brute" % d, "docs": docs,
                    "supplementary": summaries(os.path.join(d, "brute", "supplementary"))}
    return None


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
            for a in args:
                if a not in self.inputs:
                    fail("%s: the requirement %r names %r, which is not an input" % (where, req, a))
            if len(args) != {"abs_ge": 2, "ball": 2}.get(m.group(1), 1):
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
            fields = set(e) - {"kind"}
            if not required <= fields or fields - required - optional:
                fail("%s: a %s claim has the fields %s; this script knows %s" % (
                    where, kind, sorted(fields), sorted(required | optional)))
            for c in e.get("finite_when", []):
                if set(c) != KNOWN_CONDITION_FIELDS or not isinstance(c["exp"], int):
                    fail("%s: the finite_when condition %r is not one this script knows" % (where, c))
                parse(c["abs_le"], "%s, finite_when" % where, set(self.inputs))
            if kind != "makes_ball" and self.value is None:
                fail("%s: a %s claim needs a value, and the kernel has none" % (where, kind))
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

    def expr(self, text, where, names=None):
        return parse(text, "kernel %s, %s" % (self.name, where), names or self.names)

    def ball_names(self):
        """{(center, radius): ball name} of the encloses claims, to name the balls of requirements."""
        out = {}
        for e in self.entry["ensures"]:
            if e["kind"] == "encloses":
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
        fail("kernel %s: the requirement %s has no reading in the extended domain" % (self.name, kind))

    def extended_free_inputs(self):
        """The one-limb inputs no requirement constrains: in the extended domain, any value of T."""
        covered = {a for _, args in self.requires for a in args}
        return [i for i in self.inputs if i not in covered and len(self.limbs(i)) == 1]

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

    def encloses_text(self, e):
        balls = e["balls"]
        names = set(balls) | set(self.inputs)
        for b, cr in balls.items():
            if set(cr) != {"center", "radius"} or cr["center"] not in self.inputs or cr["radius"] not in self.inputs:
                fail("kernel %s: the ball %r of an encloses claim is not a center and a radius of the inputs"
                     % (self.name, b))
        s = self.expr(e["set"], "encloses", names)
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
            return text + (", " + when if when else "")
        if kind == "leading_rounded":
            return "$%s = \\mathrm{RN}(%s)$" % (name_tex(self.lead_limb(e["of"])), tex(self.value))
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
            rel = self.relation(e)
            if short:
                return "exactly whether $%s$" % rel
            return "$%s$ is true exactly when $%s$, for the exact values" % (name_tex(e["of"]), rel)
        if kind == "encloses":
            if short:
                return "contains every $%s$" % tex(self.expr(e["set"], "encloses", set(e["balls"]) | set(self.inputs)))
            return self.encloses_text(e)
        fail("kernel %s: the claim kind %r has no reading on finite operands" % (self.name, kind))

    def relation(self, e):
        if e["rel"] not in KNOWN_RELS or len(e["args"]) != 2:
            fail("kernel %s: the predicate %r has no template" % (self.name, e["rel"]))
        a, b = (tex(self.expr(x, "predicate")) for x in e["args"])
        return "%s %s %s" % (a, KNOWN_RELS[e["rel"]], b)

    def finite_short(self):
        entries = self.finite_entries
        parts = [self.finite_bullet(e, short=True) for e in entries
                 if e["kind"] != "normalized" and not (e["kind"] == "error" and e["when"])]
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
        """The oracle's label of an ensures entry, as the brute-force summaries print it."""
        kind = e["kind"]
        if kind == "error":
            return "error(%s) form %s, c=%s, k=%s, t=%s%s" % (
                e["of"], e["form"], e["c"], e["k"], e["t"], ", when %s" % e["when"] if e["when"] else "")
        if kind in ("normalized", "leading_rounded", "represents"):
            return "%s(%s)" % (kind, e["of"])
        if kind == "rounded":
            return "rounded(%s) %s" % (e["of"], e["mode"])
        if kind == "upper":
            return "upper(%s) gaps=%s" % (e["of"], e["gaps"])
        if kind == "predicate":
            return "predicate(%s) %s(%s)" % (e["of"], e["rel"], ", ".join(e["args"]))
        if kind == "encloses":
            return "encloses(%s, %s) %s over %s" % (e["center"], e["radius"], e["set"], ", ".join(
                "%s=[%s +- %s]" % (b, cr["center"], cr["radius"]) for b, cr in e["balls"].items()))
        return "%s(%s)" % (kind, e.get("of", ""))


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
    """What the stored runs say about one kernel, merged over machines and runners; then the rows
    of the supplementary runs that judged it, apart (they may judge a later form of its claims)."""
    if brute is None:
        return None
    main = brute_rows(name, brute["docs"], "")
    sup = brute_rows(name, brute.get("supplementary", []), ", supplementary run")
    if main is None and sup is None:
        return None
    out = main or {"rows": [], "findings": [], "extended": False}
    if sup:
        for r in sup["rows"]:
            r["supplementary"] = True
        out["rows"] += sup["rows"]
        out["findings"] += sup["findings"]
        out["supplementary"] = sorted({c[:7] for d in brute["supplementary"] for c in d.get("commit", [])
                                       if name in d["compiled"]["kernels"]
                                       or any(r["kernel"] == name for r in d["interp"]["enumerations"])})
    return out


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
    for d in docs:
        for r in d["interp"]["enumerations"]:
            if r["kernel"] != name:
                continue
            if interp is None:
                interp = {"title": "toy formats, every operand" + suffix, "domains": 0, "complete": 0, "formats": [],
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
             "include/kairn/gen/bounds.hpp, proofs/gen/, proofs/audit/, %s and "
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
        self.bounds = load_bounds(root)
        self.statements = load_statements(root)
        self.allowed_axioms, self.audited = load_audit(root)
        # The generated formal models (the real one, and the IEEE one where it exists) and the
        # kernels each defines.
        self.models = []
        for f in ("Model.v", "IeeeModel.v"):
            path = os.path.join(root, "proofs", "gen", f)
            if os.path.exists(path):
                self.models.append((f, set(re.findall(r"^Definition (\w+) ", read(path), re.M))))
        self.kernels = {}
        entries = load_claims(root, claims)
        self.all_names = {e["name"] for e in entries}
        for entry in entries:
            name = entry["name"]
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
        self.callers = {}
        for k in self.kernels.values():
            for callee in k.calls(self.all_names):
                self.callers.setdefault(callee, []).append(k.name)
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
        return GENERATED % ("%s/" % self.brute["dir"] if self.brute else "results/")

    def link(self, name, frm=""):
        if name in self.kernels:
            return "[`%s`](%s%s.md)" % (name, frm, name)
        return "`%s`" % name

    def not_called(self, name):
        """An entry kernel with no form in the table: one the public headers do not call yet."""
        return not self.ops.KERNELS[name]["forms"] and self.kernels[name].listing["fields"].get("entry") == "yes"

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
            w("**UNVERIFIED: no proof is checked.** The statement below is a target: %s. %s "
              "([What holds today](../getting-started/guarantees.md#proved-and-unverified))." % (
                  "Rocq has not checked a proof of it" if k.extended else
                  "the oracle tests it, but Rocq has not checked a proof of it", calls))
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
            users = k.constants_of()
            if users:
                w(self.ball_constants(k, users))
            w(self.precision(k, extended=False))
        else:
            w("For operands that satisfy the requirements, finite, infinite or NaN:")
            w("")
            w(self.extended_statement(k))
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
            if p["note"]:
                text += " " + p["note"]
            return text
        callers = self.callers.get(name, [])
        text = "No public operation computes this kernel on its own."
        if callers:
            text += " It is part of %s." % ", ".join(self.link(c) for c in callers)
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
            lines.append((k.inputs.index(a), "$%s$ is any value of `T`: a number, $\\pm\\infty$ or a NaN"
                          % name_tex(a)))
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
            if not represents:
                lines.append("$%s$ %s canonical." % ("$, $".join(name_tex(o) for o in outs),
                                                      "is" if len(outs) == 1 else "are"))
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
            elif kind == "extends":
                lines.extend(self.extended_extends(k, x))
            elif kind == "encloses":
                lines.extend(self.extended_encloses(k, x))
            elif kind == "makes_ball":
                lines.extend(self.extended_makes_ball(k, x))
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
        return ["If every operand is finite: %s ($\\Omega$ is the largest finite number of `T`)." % what,
                "If an operand is infinite or NaN: $%s = %s$." % (t, tex(self.leading(k, k.value)))]

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

    def extended_makes_ball(self, k, x):
        frm = x["from"]
        if set(frm) != {"center", "radius"} or frm["center"] not in k.inputs or frm["radius"] not in k.inputs:
            fail("kernel %s: the from of a makes_ball claim is not a center and a radius of the inputs" % k.name)
        c, r = name_tex(frm["center"]), name_tex(frm["radius"])
        return ["The result $Z$, of center $%s$ and radius $%s$, is a canonical ball." % (
                    name_tex(x["center"]), name_tex(x["radius"])),
                "$Z$ is the empty set (every limb a NaN) when $%s$ is a NaN or negative, $-\\infty$ included." % r,
                "Otherwise $Z$ is the whole line (center 0, radius $+\\infty$) when $%s$ is not finite or "
                "$%s = +\\infty$." % (c, r),
                "Otherwise $Z$ is the ball of center $%s$ and radius $%s$, exactly." % (c, r)]

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
            elif x["kind"] == "makes_ball":
                parts.append("the ball of center $%s$ and radius $%s$, canonical" % (
                    name_tex(x["from"]["center"]), name_tex(x["from"]["radius"])))
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
        rows = b["rows"]
        judged_labels = next((r["entries"] for r in rows if r["entries"]), None)
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
        cols = []
        if k.extended and b["extended"]:
            # The oracle's entries: the kernel's own, in the order of its claims, then those of the core
            # of an `extends` entry, labelled "F2, core K: ..." (oracle/kairn_oracle/extended.py). An
            # entry's oracle label starts with the claim's own label and may add the classes it judges.
            own = k.entry["ensures"]
            if judged_labels is not None and (
                    [x["kind"] for x in judged_labels[:len(own)]] != [e["kind"] for e in own]
                    or any(e["kind"] in ("error", "upper", "encloses", "rounded", "predicate", "normalized")
                           and not x["label"].startswith(k.label(e)) for x, e in zip(judged_labels, own))):
                w("**These runs judged other claims.** They judged %s; the kernel now claims %s. Their numbers "
                  "are not about the statement above." % (
                      "; ".join("`%s`" % x["label"] for x in judged_labels),
                      "; ".join("`%s`" % k.label(e) for e in own)))
                w("")
            # A condition finite_when (B4: finite operands under it give a finite ball) that the
            # claims gained after the runs: the oracle labels an entry without one "finite when
            # nothing".
            no_b4 = judged_labels is not None and any(
                e.get("finite_when") and "finite when nothing" in x["label"] for x, e in zip(judged_labels, own))
            if no_b4:
                sup = b.get("supplementary")
                w("**The condition of this claim was not judged by every run.** The claims gained it (B4: finite "
                  "operands under the condition give a finite ball) after the main runs, which judged the "
                  "kernel without it, with no condition claimed%s." % (
                      "; the supplementary run%s at commit %s judged it, on the cases of its rows below" % (
                          "s" if len(sup) > 1 else "", ", ".join("`%s`" % c for c in sup)) if sup else
                      "; no stored run judged it"))
                w("")
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
            current = [k.label(x) for x in judged]
            if judged_labels is not None and [x["label"] for x in judged_labels] != current:
                w("**These runs judged other claims.** They judged %s; the kernel now claims %s. Their numbers "
                  "are not about the statement above." % (
                      "; ".join("`%s`" % x["label"] for x in judged_labels), "; ".join("`%s`" % c for c in current)))
                w("")
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
        w("Every public operation of Kairn, grouped by what it does, with the kernel that computes it, and "
          "the kernels that the public headers do not call yet. Each kernel has a page: its statement in "
          "plain mathematics, the C++ forms that reach it, what it requires, what is proved and with which "
          "theorem, its listing, and what the latest brute-force runs measured. "
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
                else:
                    ops = "none (internal)"
                operands = operand_types(forms[0]) if forms else "-"
                status = "" if k.proved else " **UNVERIFIED**"
                rows.append("| %s | %s | %s | %s%s |" % (ops, operands, self.short(k), self.link(name), status))
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
        return "\n".join(out)

    def nav(self):
        lines = [NAV_BEGIN, "  - Reference:", "      - reference/index.md", "      - How to read a page: reference/reading.md",
                 "      - C++ API: %s" % API_PAGE]
        for gid, title, _ in self.groups:
            names = [n for n, p in self.ops.KERNELS.items() if p["group"] == gid]
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


def plan(root, claims=None):
    """{relative path: content} of every file the script owns, mkdocs.yml included."""
    site = Site(root, claims)
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
