#!/usr/bin/env python3
"""The tests of docs/tools/reference.py and of its table, docs/tools/reference_operations.py.

  python3 docs/tools/test_reference.py      (ctest's full tier: full.tools.docs.reference.test)

- The table against the data: every kernel it names is in gen/claims.json, every public
  operation of include/kairn/*.hpp whose comment names a kernel (`(kernel add_2_2)`,
  `kernels sub_2_1 and sub_1_2`) is one of that kernel's forms, or of its traits entries, and a
  kernel has forms only if the headers name or call it, so that a kernel the headers do not call
  yet is listed as such.
- The tool on modified copies of its inputs: it fails, naming what it cannot print, on an unknown
  claim kind, requirement, field, condition, lead or status, on a kind or requirement outside its
  domain, and on a kernel the table does not have; --check fails on a stale, missing or stray page
  and on a stale nav, and keeps the hand-written pages of PAGES, in the nav of their group; an
  UNVERIFIED kernel is marked; runs that judged other claims are flagged;
  the statements of the extended domain (F1 to F5, B1 to B4, the constructors) are printed with
  the kernel's own names, conditions and core; the axioms are those of the audit's allow-list, and
  a proved theorem that no audit file prints fails; every form of ldexp beyond the powers of two
  says that its steps are not machine-checked; the C++ API is in the nav and the index.

Python 3 standard library only; no network, no compiler.
"""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reference  # noqa: E402

ROOT = reference.ROOT


# --- The public headers -------------------------------------------------------------------------

def split_params(text):
    """Parameters at the top level of a parameter list (Expansion<T, 2> holds a comma)."""
    out, depth, cur = [], 0, ""
    for ch in text:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


def param_type(param, context):
    t = re.sub(r"\bconst\b|&", " ", param)
    t = re.sub(r"\s+[A-Za-z_]\w*\s*$", "", t.strip())     # the parameter's name
    t = re.sub(r"\s+", " ", t).strip()
    t = t.replace("std::type_identity_t<T>", "T")
    if t == "Expansion" and context and context.startswith("Expansion<"):
        return context
    if t == "Ball":
        return "Ball<T, K>"
    if t == "Interval":
        return "Interval<T, K>"
    return t


KERNEL_WORDS = re.compile(r"\b[Kk]ernels?\s+([a-z][a-z0-9_]*(?:(?:\s*,\s*|\s+or\s+|\s+and\s+)[a-z][a-z0-9_]*)*)")


def kernels_named(comment, known):
    names = []
    for m in KERNEL_WORDS.finditer(comment):
        for n in re.split(r"\s*,\s*|\s+or\s+|\s+and\s+", m.group(1)):
            if (n in known or re.search(r"_\d", n)) and n not in names:
                names.append(n)
    return names


def header_operations(root, known):
    """[(where, key, kernels)] for every public declaration whose /// comment names a kernel; key
    is ('op', name, operand types) for an operation and ('traits', 'traits<...>::member')."""
    found = []
    for fname in ("expansion.hpp", "ball.hpp", "interval.hpp", "traits.hpp", "blocks.hpp"):
        path = os.path.join(root, "include", "kairn", fname)
        lines = reference.read(path).split("\n")
        context, detail, comment, prefix = None, False, [], ""
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if s.startswith("namespace detail {"):
                detail = True
            elif s.startswith("}  // namespace detail"):
                detail = False
            elif s.startswith("namespace finite {"):
                prefix = "finite::"                              # kairn::finite::add(x, y)
            elif s.startswith("}  // namespace finite"):
                prefix = ""
            m = re.match(r"(?:struct|class) (Expansion<T, [12]>|Ball|Interval|traits_one_limb|traits<Expansion<T, 2>>) \{",
                         s)
            if m:
                context = {"Ball": "Ball<T, K>", "Interval": "Interval<T, K>",
                           "traits_one_limb": "traits<T>"}.get(m.group(1), m.group(1))
                comment = []
                continue
            if s == "};":
                context = None
            if s.startswith("///"):
                comment.append(s[3:].strip())
                continue
            if s.startswith("#"):
                comment = []        # the comment of a file (`/// @file`) or of a macro, not of an operation
                continue
            if not comment or s.startswith("template <") or s.startswith("requires") or not s:
                continue
            text, comment = " ".join(comment), []
            if detail and not (context or "").startswith("traits"):
                continue
            names = kernels_named(text, known)
            if not names:
                continue
            where = "include/kairn/%s:%d" % (fname, i)
            t = re.match(r"static constexpr auto (\w+) =", s)
            if t:
                found.append((where, ("traits", "%s::%s" % (context, t.group(1))), names))
                continue
            # A function of traits (the bounds as functions of the length): traits<...>::name(n).
            t = re.match(r"static constexpr auto (\w+)\(([^)]*)\)", s)
            if t and (context or "").startswith("traits"):
                operands = tuple(param_type(p, context) for p in split_params(t.group(2)))
                found.append((where, ("op", "%s::%s" % (context, t.group(1)), operands), names))
                continue
            f = re.search(r"(operator(?:\+=|-=|\*=|==|!=|<=|>=|[-+*<>])|\b[A-Za-z_]\w*)\(([^)]*)\)", s)
            if not f:
                raise AssertionError("%s: cannot read the declaration %r" % (where, s))
            name = f.group(1)
            if context and name == context.split("<")[0]:
                name = context                                   # a constructor
            elif not context:
                name = prefix + name
            operands = tuple(param_type(p, context) for p in split_params(f.group(2)))
            found.append((where, ("op", name, operands), names))
    return found


def header_kernel_uses(root, known):
    """(named, called): the kernels the /// comments of the public headers name for an operation,
    and those the headers call as kairn::gen functions or gate on (gen::bounds::K)."""
    named = set()
    for _, _, names in header_operations(root, known):
        named |= set(names)
    called = set()
    d = os.path.join(root, "include", "kairn")
    for fname in os.listdir(d):
        if fname.endswith(".hpp"):
            text = reference.read(os.path.join(d, fname))
            called |= set(re.findall(r"\bgen::(\w+)\(", text)) & known
            called |= set(re.findall(r"\bgen::bounds::(\w+)<", text)) & known
    return named, called


def form_key(f):
    code = f["code"]
    m = re.fullmatch(r"(\w+) (\+=|-=|\*=|==|!=|<=|>=|[-+*<>]) (\w+)", code)
    if m:
        return ("op", "operator" + m.group(2), tuple(f["operands"]))
    m = re.fullmatch(r"-(\w+)", code)
    if m:
        return ("op", "operator-", tuple(f["operands"]))
    m = re.fullmatch(r"(traits<.*>::\w+)\((.*)\)", code)  # a function of traits: traits<X>::sum(n)
    if m:
        return ("op", m.group(1), tuple(f["operands"]))
    m = re.fullmatch(r"\w+\.(\w+)(?:<[^>]*>)?\((?:\w+(?:, \w+)*)?\)", code)  # a member function, X.name(), X.name<T>(), X.name(Y, Z)
    if m:
        return ("op", m.group(1), tuple(f["operands"][1:]))
    m = re.fullmatch(r"([\w:]+(?:<[^>]*>)?)\((.*)\)", code)
    if m:
        return ("op", m.group(1), tuple(f["operands"]))
    raise AssertionError("cannot read the form %r" % code)


def table_problems(found, kernels, claims):
    """The header operations that name a kernel and are not in the table under that kernel."""
    problems = []
    for where, key, names in found:
        for k in names:
            if k not in claims:
                problems.append("%s names the kernel %s, which gen/claims.json does not have" % (where, k))
                continue
            if k not in kernels:
                problems.append("%s: %s is not in the table" % (where, k))
                continue
            p = kernels[k]
            if key[0] == "traits":
                if key[1] not in p["traits"]:
                    problems.append("%s: %s is not among the traits of %s in the table" % (where, key[1], k))
                continue
            keys = {form_key(f) for f in p["forms"]}
            variants = {(key[0], key[1].replace("K", n), tuple(t.replace("<T, K>", "<T, %s>" % n) for t in key[2]))
                        for n in ("1", "2")}
            if not keys & variants:
                problems.append("%s: %s%s, which names %s, is not a form of %s in the table"
                                % (where, key[1], list(key[2]), k, k))
    return problems


class Table(unittest.TestCase):
    """docs/tools/reference_operations.py against gen/claims.json and the headers."""

    @classmethod
    def setUpClass(cls):
        cls.ops = reference.load_operations(ROOT)
        cls.claims = {k["name"]: k for k in reference.load_claims(ROOT)}

    def test_every_kernel_of_the_table_exists(self):
        missing = [k for k in self.ops.KERNELS if k not in self.claims]
        self.assertEqual(missing, [], "kernels in the table that gen/claims.json does not have")

    def test_every_kernel_has_a_page(self):
        missing = [k for k in self.claims if k not in self.ops.KERNELS]
        self.assertEqual(missing, [], "kernels of gen/claims.json that the table does not have")

    def test_forms_only_for_kernels_the_headers_use(self):
        named, called = header_kernel_uses(ROOT, set(self.claims))
        self.assertIn("add_2_2", called)
        self.assertIn("add_1_1", named)
        unused = [k for k, p in self.ops.KERNELS.items() if p["forms"] and k not in named | called]
        self.assertEqual(unused, [], "kernels with forms in the table that no header names or calls")

    def test_kernels_not_called_yet_are_not_called(self):
        named, called = header_kernel_uses(ROOT, set(self.claims))
        entry = [k for k, p in self.ops.KERNELS.items() if not p["forms"] and reference.load_listing(
            ROOT, k)["fields"].get("entry") == "yes"]
        self.assertIn("ball_add_2", entry)
        used = [k for k in entry if k in named | called]
        self.assertEqual(used, [], "kernels the headers name or call, listed in the table without forms "
                                   "(their pages would say that no header calls them)")

    def test_the_steps_of_ldexp_are_said_to_be_not_machine_checked(self):
        # Beyond the powers of two of T, ldexp is a composition written in the header (deviation 17):
        # every form that computes it says so, in the same words.
        steps = [(name, f["code"]) for name, p in self.ops.KERNELS.items() for f in p["forms"]
                 if "ldexp(" in f["code"] and "itself" not in (f["note"] or "")]
        self.assertEqual(sorted(steps), [("ball_mul_pow2_1_full", "ldexp(X, n)"), ("ball_mul_pow2_2_full", "ldexp(X, n)"),
                                         ("mul_1_1", "ldexp(a, n)"), ("mul_pow2_2", "finite::ldexp(x, n)"),
                                         ("mul_pow2_2_full", "ldexp(x, n)")])
        for name, code in steps:
            note = next(f["note"] for f in self.ops.KERNELS[name]["forms"] if f["code"] == code)
            self.assertIn(self.ops.COMPOSITION, note, "%s, %s" % (name, code))

    def test_every_form_can_be_read(self):
        for name, p in self.ops.KERNELS.items():
            for f in p["forms"]:
                form_key(f)

    def test_every_operation_of_the_headers_is_in_the_table(self):
        found = header_operations(ROOT, set(self.claims))
        self.assertGreater(len(found), 60, "the header scan finds too few operations: it is broken")
        self.assertEqual(table_problems(found, self.ops.KERNELS, self.claims), [])

    def test_a_form_missing_from_the_table_is_caught(self):
        found = header_operations(ROOT, set(self.claims))
        kernels = json.loads(json.dumps(self.ops.KERNELS))
        kernels["lt_2_2"]["forms"] = [f for f in kernels["lt_2_2"]["forms"] if f["code"] != "y > x"]
        kernels["sub_1_2"]["traits"] = []
        problems = table_problems(found, kernels, self.claims)
        self.assertEqual(len(problems), 2, problems)
        self.assertIn("operator>", problems[0])
        self.assertIn("sub_limb", problems[1])
        found.append(("include/kairn/expansion.hpp:1", ("op", "operator/", ("Expansion<T, 2>",) * 2), ["div_2_2"]))
        self.assertIn("div_2_2, which gen/claims.json does not have", table_problems(found, kernels, self.claims)[-1])

    def test_the_header_scan_sees_what_it_should(self):
        found = header_operations(ROOT, set(self.claims))
        keys = {(key, tuple(k)) for _, key, k in found}
        self.assertIn((("op", "operator+", ("Expansion<T, 2>", "Expansion<T, 2>")), ("add_2_2_full",)), keys)
        self.assertIn((("op", "finite::add", ("Expansion<T, 2>", "Expansion<T, 2>")), ("add_2_2",)), keys)
        self.assertIn((("op", "Expansion<T, 1>", ("Expansion<T, 2>",)), ("to_nearest_2",)), keys)
        self.assertIn((("op", "Expansion<T, 2>", ("T",)), ("make_2",)), keys)
        self.assertIn((("op", "operator+", ("Ball<T, K>", "Ball<T, K>")), ("ball_add_1_full", "ball_add_2_full")), keys)
        self.assertIn((("op", "Ball<T, K>", ("Expansion<T, K>", "T")), ("ball_make_1", "ball_make_2")), keys)
        self.assertIn((("op", "two_sum", ("T", "T")), ("two_sum_entry",)), keys)
        self.assertIn((("op", "certainly_positive", ()), ("lt_1_2",)), keys)
        self.assertIn((("op", "Ball<T, K>", ("Constant<Expansion<T, K>>",)), ("ball_make_1", "ball_make_2")), keys)
        self.assertIn((("traits", "traits<Expansion<T, 2>>::sub_limb"), ("sub_2_1", "sub_1_2")), keys)
        # Intervals, and the functions of a Ball of the interface the two share.
        self.assertIn((("op", "operator*", ("Interval<T, K>", "Interval<T, K>")), ("interval_mul_1", "interval_mul_2")),
                      keys)
        self.assertIn((("op", "Interval<T, K>", ("Expansion<T, K>", "Expansion<T, K>")),
                       ("interval_make_1", "interval_make_2")), keys)
        self.assertIn((("op", "hull", ("Interval<T, K>",)), ("interval_hull_1", "interval_hull_2")), keys)
        self.assertIn((("op", "split", ()), ("interval_split_1",)), keys)
        self.assertIn((("op", "lower_as", ()), ("to_down_2",)), keys)
        self.assertIn((("op", "lower_as", ()), ("ball_lower_as_1", "ball_lower_as_2")), keys)
        self.assertIn((("op", "Ball<T, K>", ("Interval<T, K>",)), ("interval_to_ball_1",)), keys)
        self.assertIn((("op", "Ball<T, K>", ("Ball<T, 2>",)), ("ball_narrow_2_1",)), keys)
        self.assertIn((("op", "from_interval", ("T", "T")), ("ball_from_interval_2",)), keys)


# --- The tool on modified copies ---------------------------------------------------------------

COPIED = ["gen/claims.json", "gen/kernels", "include/kairn/gen/bounds.hpp", "results",
          "docs/tools/reference_operations.py", "docs/developer/design/phase0/references.md",
          "docs/developer/results", "proofs/theories", "proofs/gen/Statements.v", "proofs/gen/Model.v",
          "proofs/gen/IeeeModel.v", "proofs/gen/Audit.v", "proofs/gen/IeeeAudit.v", "proofs/audit",
          "mkdocs.yml",
          "docs/reference"]


IEEE_ONLY = ("make_2", "make_2_limbs", "ball_make_1", "ball_make_2")


def with_ieee_only(data):
    """The claims with "ieee_only": true on the kernels without a real-model statement (the *_full
    kernels and the constructors), as the generator is to write them; unchanged once it does."""
    if not any("ieee_only" in k for k in data["kernels"]):
        for k in data["kernels"]:
            if k["name"].endswith("_full") or k["name"] in IEEE_ONLY:
                k["ieee_only"] = True
    return data


class Copy:
    """A copy of the inputs of reference.py in a temporary directory, with ieee_only in its claims,
    and the pages written from them, so that every test starts from a fresh reference."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="kairn-reference-")
        for rel in COPIED:
            src, dst = os.path.join(ROOT, rel), os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy(src, dst)
        self.set_claims(with_ieee_only(self.claims()))
        reference.write(self.root)

    def claims(self):
        with open(os.path.join(self.root, "gen", "claims.json"), encoding="utf-8") as f:
            return json.load(f)

    def set_claims(self, data):
        with open(os.path.join(self.root, "gen", "claims.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def kernel(self, data, name):
        return next(k for k in data["kernels"] if k["name"] == name)

    def path(self, rel):
        return os.path.join(self.root, rel)

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


class Tool(unittest.TestCase):
    def setUp(self):
        self.copy = Copy()

    def tearDown(self):
        self.copy.close()

    def fails(self, *words):
        with self.assertRaises(reference.ReferenceError) as ctx:
            reference.plan(self.copy.root)
        for w in words:
            self.assertIn(w, str(ctx.exception))
        return str(ctx.exception)

    def change(self, name, edit):
        """Apply edit to the claims of one kernel in the copy."""
        data = self.copy.claims()
        edit(self.copy.kernel(data, name))
        self.copy.set_claims(data)

    def page(self, name):
        return reference.plan(self.copy.root)["docs/reference/%s.md" % name]

    def test_the_copy_is_fresh(self):
        self.assertEqual(reference.check(self.copy.root), [])

    def test_unknown_claim_kind(self):
        data = self.copy.claims()
        self.copy.kernel(data, "add_2_2")["ensures"].append({"kind": "frobnicates", "of": "z"})
        self.copy.set_claims(data)
        self.fails("add_2_2", "frobnicates", "template")

    def test_unknown_requirement(self):
        data = self.copy.claims()
        self.copy.kernel(data, "mul_2_2")["requires"].append("canonical(x)")
        self.copy.set_claims(data)
        self.fails("mul_2_2", "canonical(x)")

    def test_unknown_status(self):
        data = self.copy.claims()
        self.copy.kernel(data, "neg_2")["status"] = "pending"
        self.copy.set_claims(data)
        self.fails("neg_2", "pending")

    def test_unknown_field(self):
        self.change("neg_2", lambda k: k.update(frobnication=1))
        self.fails("neg_2", "frobnication")

    def test_ieee_fields_on_a_finite_kernel(self):
        self.change("add_2_2", lambda k: k.update(ieee_status="proved"))
        self.fails("add_2_2", "ieee_status")

    def test_extended_kind_in_the_finite_domain(self):
        self.change("add_2_2", lambda k: k["ensures"].append({"kind": "represents", "of": "z"}))
        self.fails("add_2_2", "represents", "finite domain")

    def test_extended_requirement_in_the_finite_domain(self):
        self.change("ball_add_2", lambda k: k["requires"].append("ball(cx, rx)"))
        self.fails("ball_add_2", "ball(cx, rx)", "finite domain")

    def test_finite_kind_without_extended_reading(self):
        self.change("neg_2", lambda k: k["ensures"].append({"kind": "leading_rounded", "of": "z"}))
        self.fails("neg_2", "leading_rounded", "extended domain")

    def test_unknown_field_of_a_claim(self):
        self.change("add_2_2_full", lambda k: k["ensures"][0].update(scale=2))
        self.fails("add_2_2_full", "extends", "scale")

    def test_unknown_condition(self):
        self.change("add_2_2_full", lambda k: k["ensures"][0]["finite_when"][0].update(strict=True))
        self.fails("add_2_2_full", "finite_when")

    def test_unknown_lead(self):
        self.change("mul_2_1_full", lambda k: k["ensures"][0].update(lead="div"))
        self.fails("mul_2_1_full", "div")

    def test_core_with_other_inputs(self):
        self.change("add_2_2_full", lambda k: k["ensures"][0].update(core="add_2_1"))
        self.fails("add_2_2_full", "add_2_1", "inputs")

    def test_statuses_of_a_full_kernel_disagree(self):
        self.change("add_2_2_full", lambda k: k.update(status="unverified"))
        self.fails("add_2_2_full", "ieee_status")

    def test_proved_ieee_statement_needs_its_theorem(self):
        self.change("neg_2", lambda k: (k.update(ieee_status="proved"), k.pop("ieee_theorem", None)))
        self.fails("neg_2", "ieee_theorem")

    def test_proved_ieee_statement(self):
        self.change("neg_2", lambda k: k.update(ieee_status="proved", ieee_theorem={
            "file": "proofs/theories/Sign.v", "name": "neg_2_correct"}))
        page = self.page("neg_2")
        self.assertIn("proved for finite operands · proved for infinite and NaN operands", page)
        self.assertIn("**Status of this statement:** proved.", page)
        self.assertNotIn(reference.IEEE_PROOFS_SENTENCE, page)

    def test_constructor_without_value(self):
        self.change("make_2", lambda k: k.pop("value"))
        self.fails("make_2", "value")

    def test_full_kernel(self):
        page = self.page("add_2_2_full")
        self.assertIn("| `x + y` | `Expansion<T, 2>`, `Expansion<T, 2>` |", page)
        self.assertIn("**F2.** If $w_0$ is finite", page)
        self.assertIn("$\\lvert w - (x + y)\\rvert \\le \\frac{3u^2}{1 - 4u}\\,\\lvert x + y\\rvert$", page)
        self.assertIn("$\\lvert x\\rvert \\le 2^{e_{\\max} - 2}$ and $\\lvert y\\rvert \\le 2^{e_{\\max} - 2}$", page)
        self.assertIn("$2^{1022}$ for `double`, $2^{126}$ for `float`", page)
        self.assertIn("the canonical form of $x_0 + y_0$ computed in `T`", page)
        # Unverified, its page says so and points to the proofs page.
        self.change("add_2_2_full", lambda k: (k.update(status="unverified", ieee_status="unverified"),
                                               k.pop("ieee_theorem", None)))
        self.assertIn(reference.IEEE_PROOFS_SENTENCE, self.page("add_2_2_full"))

    def test_kernel_not_called_yet(self):
        # The finite core of a Ball operation: the headers call the full kernel instead.
        page = self.page("ball_add_2")
        self.assertIn("**Not yet called by the public headers.**", page)
        self.assertIn("call [`ball_add_2_full`](ball_add_2_full.md), which computes this kernel", page)

    def test_conditions_come_from_the_claims(self):
        self.change("mul_2_1_full", lambda k: k["ensures"][0].update(finite_when=[{"abs_le": "x*a", "exp": -1}]))
        page = self.page("mul_2_1_full")
        self.assertIn("**F3.** If every operand is finite and $\\lvert x a\\rvert \\le 2^{e_{\\max} - 1}$", page)
        self.assertIn("$2^{1023}$ for `double`, $2^{127}$ for `float`", page)
        self.assertNotIn("No condition under which", page)

    def test_full_ball_kernel(self):
        page = self.page("ball_scale_2_full")
        self.assertIn("**B2.** $Z$ is empty exactly when $X$ is empty", page)
        self.assertIn("**B3.** If $Z$ is a finite ball, then $X$ is a finite ball and $a$ is finite", page)
        self.assertIn("$a$ is any value of `T`", page)
        self.assertIn("It follows that in every case $Z$ contains $x a$", page)

    def test_constructors(self):
        self.assertIn("when $a = \\pm\\infty$, $x = (\\pm\\infty, 0)$", self.page("make_2"))
        self.assertIn("$Z$ is the empty set (every limb a NaN) when $r$ is negative, $-\\infty$ included.",
                      self.page("ball_make_2"))
        self.assertIn("the whole line (center 0, radius $+\\infty$) when $r$ is a NaN or $+\\infty$",
                      self.page("ball_make_1"))

    def test_unknown_set_operation(self):
        # A set operation this script has no template for is an error, never a guess (stage B1).
        self.change("interval_hull_1", lambda k: k["ensures"][0].update(set="xor"))
        self.fails("interval_hull_1", "xor")

    def test_unknown_set_relation(self):
        # A relation of a predicate of sets that this script has no template for is an error (stage
        # B2), and so is a trit of a relation without a three-valued reading.
        self.change("interval_subset_1", lambda k: k["ensures"][0].update(rel="near"))
        self.fails("interval_subset_1", "near")
        self.change("interval_less_1", lambda k: k["ensures"][0].update(rel="subset"))
        self.fails("interval_less_1", "subset")

    def test_set_predicates(self):
        # Stage B2: the predicates (certain) and the three-valued comparisons (trit) of an interval.
        self.assertIn("$m$ is true exactly when the point $t$ is a finite number and a member of $X$: the answer "
                      "is exact.", self.page("interval_contains_1"))
        self.assertIn("$m$ is true exactly when $X \\subseteq Y$, every member of $X$ a member of $Y$",
                      self.page("interval_subset_2"))
        self.assertIn("$m$ is true exactly when $0 < x$ for every $x \\in X$, $X$ not being empty",
                      self.page("interval_positive_1"))
        self.assertIn("every member of $X$ is in the interior of $Y$", self.page("interval_rel_interior_1"))
        page = self.page("interval_less_equal_2")
        self.assertIn("never both. Both false is the answer *unknown*.", page)
        self.assertIn("*unknown* is returned exactly when neither holds.", page)
        self.assertIn("$\\mathit{no}$ only if", page)
        # Of a ball: certain for two limbs, exact under a condition for one.
        page = self.page("ball_contains_point_2")
        self.assertIn("the point is not a finite number, the answer is exact", page)
        self.assertIn("certain, not exact.", page)
        self.assertIn("$\\lvert r_x + r_y\\rvert \\le \\Omega$, the answer is exact as well.", self.page("ball_less_1"))
        self.assertIn("$m$ is true only if $Y \\subseteq X$", self.page("ball_contains_ball_2"))
        # The set operations of a ball.
        self.assertIn("when $X$ is empty, $Z$ is $Y$ as it is (the same limbs); when $Y$ is empty and $X$ is not, "
                      "$Z$ is $X$ as it is", self.page("ball_hull_1"))
        self.assertIn("when $X$ is the whole line, $Z$ is $Y$ as it is (the same limbs); when $Y$ is the whole line "
                      "and $X$ is not, $Z$ is $X$ as it is", self.page("ball_intersection_1"))
        self.assertIn("when $X$ is empty, $Z$ is $Y$ as it is", self.page("ball_hull_2"))
        self.assertIn("when $Y$ is the whole line and $X$ is not", self.page("ball_intersection_2"))
        index = self.page("index")
        self.assertIn("when X is empty, Z is Y as it is (the same limbs); when Y is empty and X is not, Z is X as it "
                      "is", index)
        self.assertIn("when X is the whole line, Z is Y as it is (the same limbs); when Y is the whole line and X is "
                      "not, Z is X as it is", index)
        self.assertNotIn("gives the other", index)
        self.assertIn("is a member of the first part", self.page("ball_split_2"))
        # The conversions of two limbs.
        self.assertIn("The radius $r$ may be $+\\infty$ for a bounded interval near the top of the range",
                      self.page("interval_mid_rad_2"))
        self.assertIn("In every case the midpoint $m$ is a canonical number of two limbs", self.page("interval_mid_rad_2"))
        self.assertNotIn("canonical number of two limbs", self.page("interval_mid_rad_1"))
        self.assertIn("When $c - r = 0$, $z_l = c - r$ exactly.", self.page("ball_to_interval_2"))
        self.assertIn("the smallest radius of `T` for that center", self.page("ball_from_interval_1"))

    def test_interval_kernels(self):
        # The claims of the interval kernels (architecture.md, "Claims of the interval kernels").
        page = self.page("interval_mul_1")
        self.assertIn("**I3.** $Z$ contains $x y$ for every $x \\in X$, $y \\in Y$", page)
        self.assertIn("$z_l$ is $\\mathrm{RD}(\\ell)$ or at most 1 step of `T` below it", page)
        self.assertIn("**I5.** For bounded $X$ and $Y$, $Z$ is bounded exactly when", page)
        page = self.page("interval_add_2")
        self.assertIn("| $A / u^2$ | $8.0000000000000091 \\times 10^{0}$ |", page)
        self.assertIn("for the lower bound when $x_l + y_l = 0$", page)
        self.assertIn("$\\lvert l - (x + y)\\rvert \\le A\\,\\lvert x + y\\rvert + B$", self.page("add_down_2_2"))
        self.assertIn("If the ball $X$ of center $c$ and radius $r$ is empty: $l = +\\infty$", self.page("ball_lower_as_1"))
        # Why a bound of a ball with a two-limb center claims no number of steps, and what it claims.
        for name, side in (("ball_lower_as_2", "RD}(c - r)"), ("ball_upper_as_2", "RU}(c + r)")):
            page = self.page(name)
            self.assertIn("No number of steps of `T` from $\\mathrm{%s$ is claimed" % side, page)
            self.assertIn("much smaller than $c$ in magnitude", page)
            self.assertIn("within the bound above: $\\lvert", page)
            self.assertIn("\\le 5\\,u\\,(\\lvert c\\rvert + \\lvert r\\rvert) + 3\\,\\eta$.", page)
        self.assertNotIn("No number of steps", self.page("ball_lower_as_1"))
        # Stage B1: the set operations, the conversions, the split, the zero of a product of
        # intervals, the bounds of two limbs over extended reals, not_nan of two limbs.
        self.assertIn("$Z$ is empty exactly when $X$ and $Y$ both are.", self.page("interval_hull_1"))
        self.assertIn("$Z$ is empty exactly when no real number is a member of both", self.page("interval_intersection_2"))
        page = self.page("interval_mid_rad_1")
        self.assertIn("$\\lvert m - \\tfrac{x_l + x_u}{2}\\rvert \\le u\\,\\lvert \\tfrac{x_l + x_u}{2}\\rvert + \\eta$", page)
        self.assertIn("$\\mathrm{RU}(\\max(m - x_l, x_u - m))$", page)
        self.assertIn("These are the values of `mid` and `rad` of IEEE 1788.", page)
        self.assertIn("An unbounded interval gives the whole line, center 0", self.page("interval_to_ball_1"))
        self.assertIn("$z_l = \\mathrm{RD}(c - r)$ and $z_u = \\mathrm{RU}(c + r)$", self.page("ball_to_interval_1"))
        self.assertIn("the two together are $X$, split at that point", self.page("interval_split_1"))
        self.assertIn("**I6.** For nonempty $X$ and $Y$: if an operand is $[0, 0]$, $Z$ is $[0, 0]$",
                      self.page("interval_mul_2"))
        page = self.page("mul_ext_2_2")
        self.assertIn("$l$ is never a NaN.", page)
        self.assertIn("$x$ is not a NaN: a finite normalized pair or $(\\pm\\infty, \\pm 0)$", page)
        self.assertIn("| $A / u^2$ |", page)
        self.assertIn("$Z$ is the whole line, $[-\\infty, +\\infty]$", self.page("interval_make_1"))
        # The same infinity twice is the whole line, for an interval and for a ball from an interval
        # (the owner's decision of 2026-11-20); reversed bounds the empty set.
        for name in ("interval_make_1", "interval_make_2", "ball_from_interval_2"):
            page = self.page(name)
            self.assertIn("or both are the same infinity ($[+\\infty, +\\infty]$, $[-\\infty, -\\infty]$): $Z$ is "
                          "the whole line", page)
            self.assertIn("Otherwise, if the bounds are reversed, $l_o > h_i$", page)
        self.assertIn("If an operand is a zero: $d$ is a zero", self.page("mul_dir_1"))
        # A constant of a claim this script cannot read is an error, never a guess.
        self.change("add_down_2_2", lambda k: k["ensures"][1].update(rel="up(v)"))
        self.fails("add_down_2_2", "rel")

    # ieee_only, the claims' word on whether a kernel has a statement on finite operands.
    def test_ieee_only_outside_the_extended_domain(self):
        self.change("add_2_2", lambda k: k.update(ieee_only=True))
        self.fails("add_2_2", "ieee_only", "not extended")

    def test_ieee_only_with_another_value(self):
        self.change("add_2_2_full", lambda k: k.update(ieee_only=False))
        self.fails("add_2_2_full", "ieee_only")

    def test_ieee_only_kinds_on_a_kernel_with_a_finite_statement(self):
        for name, kind in (("add_2_2_full", "extends"), ("ball_make_2", "makes_ball"), ("make_2", "represents")):
            self.change(name, lambda k: k.pop("ieee_only"))
            self.fails(name, kind, "not ieee_only")
            self.change(name, lambda k: k.update(ieee_only=True))

    def test_ieee_only_with_two_statuses(self):
        # make_2, proved in the IEEE model and without a real-model statement.
        self.change("make_2", lambda k: k.update(status="unverified"))
        self.fails("make_2", "ieee_only", "ieee_status")

    def test_ieee_only_decides_the_reading(self):
        # A kernel with a ball requirement and an encloses claim, and a real-model statement:
        # ball_neg_k, which the claims do not mark ieee_only.
        page = self.page("ball_neg_1")
        finite, extended = page.split("## Infinite and NaN operands")
        self.assertIn("proved for finite operands", page)
        self.assertIn("- $c_x$ is a number of `T`.\n- $r_x \\ge 0$.", finite)
        self.assertIn("is a canonical ball: a finite ball", extended)
        self.assertIn("**B2.** $Z$ is empty exactly when $X$ is empty", extended)
        self.assertIn("$c_x$ is normalized", self.page("ball_neg_2").split("## Infinite")[0])
        # The same claims with ieee_only: one statement, in the IEEE model, and its status.
        self.change("ball_neg_1", lambda k: k.update(ieee_only=True))
        page = self.page("ball_neg_1")
        self.assertNotIn("## Infinite and NaN operands", page)
        self.assertIn("finite, infinite or NaN", page)

    def test_represents_next_to_other_claims(self):
        page = self.page("neg_2")
        finite, extended = page.split("## Infinite and NaN operands")
        self.assertNotIn("canonical", finite.split("## Status")[0].split("## Guarantees")[1])
        self.assertIn("$z$ is canonical and is $-x$ exactly: when $-x$ is finite", extended)
        self.assertIn("when $-x = \\pm\\infty$, $z = (\\pm\\infty, 0)$", extended)
        self.assertNotIn("Which canonical value comes out", page)
        self.assertNotIn("These runs judged other claims", page)

    def test_represents_without_the_value_is_said_to_be_only_canonical(self):
        self.change("abs_2", lambda k: k.update(ensures=[e for e in k["ensures"] if e["kind"] != "represents"]))
        page = self.page("abs_2")
        self.assertIn("- $z$ is canonical.", page)
        self.assertIn("Which canonical value comes out", page)

    def test_finite_kernel_with_extended_statement(self):
        page = self.page("to_up_2")
        self.assertIn("proved for finite operands · proved for infinite and NaN operands", page)
        self.change("to_up_2", lambda k: (k.update(ieee_status="unverified"), k.pop("ieee_theorem", None)))
        page = self.page("to_up_2")
        self.assertIn("proved for finite operands · **UNVERIFIED** for infinite and NaN operands", page)
        self.assertIn("## Infinite and NaN operands", page)
        self.assertIn("If an operand is infinite or NaN: $t = x_0$", page)
        self.assertIn("$x$ is normalized", page.split("## Infinite")[0])
        self.assertIn("$x$ is canonical", page.split("## Infinite")[1])

    def test_the_sentence_on_hand_written_proofs_is_the_same_everywhere(self):
        files = reference.plan(self.copy.root)
        site = reference.Site(self.copy.root)
        for name, k in site.kernels.items():
            page = files["docs/reference/%s.md" % name]
            unverified_ieee = k.extended and not k.ieee_proved
            self.assertEqual(page.count(reference.IEEE_PROOFS_SENTENCE), 1 if unverified_ieee else 0, name)

    def test_kernel_missing_from_the_table(self):
        data = self.copy.claims()
        extra = json.loads(json.dumps(self.copy.kernel(data, "add_2_2")))
        extra["name"] = "add_2_2_twin"
        data["kernels"].append(extra)
        self.copy.set_claims(data)
        self.fails("add_2_2_twin", "reference_operations.py")

    def test_table_names_a_kernel_that_does_not_exist(self):
        data = self.copy.claims()
        data["kernels"] = [k for k in data["kernels"] if k["name"] != "rmul"]
        self.copy.set_claims(data)
        self.fails("rmul", "does not have")

    def test_kernel_description_with_a_header_line_that_is_not_a_field(self):
        path = self.copy.path("gen/kernels/neg_2.kernel")
        text = reference.read(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace("domain:", "a line without a field\ndomain:", 1))
        self.fails("neg_2.kernel", "not a field")

    def test_changes_announced_for_the_claims_need_no_template(self):
        # A guard line in add_2_1, the second radius design in ball_add_2, a condition of F3 for
        # every full kernel: the pages are regenerated, nothing fails.
        for name, old, new in (
                ("add_2_1", "(sh, sl) = two_sum(x0, a)", "g        = guard(a)\n(sh, sl) = two_sum(x0, g)"),
                ("ball_add_2", None, "(cz0, cz1) = add_2_2(cx0, cx1, cy0, cy1)\naz = abs(cz0)\ns = add(rx, ry)\n"
                                     "t = fma(az, const up(unit(add_2_2)), s)\n"
                                     "rz = fma(t, const up((1+u)^3), const up(eta))")):
            path = self.copy.path("gen/kernels/%s.kernel" % name)
            text = reference.read(path)
            if old is None:
                head, _ = text.split("\n\n", 1)
                text = head + "\n\n" + new + "\n"
            else:
                text = text.replace(old, new)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        data = self.copy.claims()
        for k in data["kernels"]:
            for e in k["ensures"]:
                if e["kind"] == "extends":
                    e["finite_when"] = [{"abs_le": k["value"], "exp": -1}]
        self.copy.set_claims(data)
        files = reference.plan(self.copy.root)
        self.assertIn("g        = guard(a)", files["docs/reference/add_2_1.md"])
        self.assertNotIn("The radius adds", files["docs/reference/ball_add_2.md"])
        self.assertIn("$\\lvert x - a\\rvert \\le 2^{e_{\\max} - 1}$", files["docs/reference/sub_2_1_full.md"])

    def test_kernel_description_with_a_new_field(self):
        # The generator's own fields (cone_exempt, guard_pending, ...) do not change the pages.
        path = self.copy.path("gen/kernels/add_2_1.kernel")
        text = reference.read(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace("entry:", "colour:        blue\nentry:", 1))
        self.assertEqual(reference.check(self.copy.root), [])

    def test_stale_page(self):
        path = self.copy.path("docs/reference/mul_2_2.md")
        with open(path, "a", encoding="utf-8") as f:
            f.write("\nA line nobody generated.\n")
        problems = reference.check(self.copy.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("mul_2_2.md", problems[0])

    def test_stale_page_after_a_claim_changes(self):
        data = self.copy.claims()
        self.copy.kernel(data, "mul_2_1")["source"]["cite"] = "another source"
        self.copy.set_claims(data)
        problems = reference.check(self.copy.root)
        self.assertTrue(any("mul_2_1.md" in p for p in problems), problems)

    def test_missing_and_stray_pages(self):
        os.remove(self.copy.path("docs/reference/split.md"))
        with open(self.copy.path("docs/reference/old_kernel.md"), "w", encoding="utf-8") as f:
            f.write("# Old\n")
        problems = reference.check(self.copy.root)
        self.assertTrue(any("split.md is missing" in p for p in problems), problems)
        self.assertTrue(any("old_kernel.md" in p for p in problems), problems)

    def test_page_missing_from_the_nav(self):
        path = self.copy.path("mkdocs.yml")
        text = reference.read(path)
        line = next(l for l in text.split("\n") if l.endswith("reference/radd.md"))
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace(line + "\n", ""))
        problems = reference.check(self.copy.root)
        self.assertEqual(problems, ["mkdocs.yml differs from what docs/tools/reference.py writes"])

    def test_the_cpp_api_is_in_the_nav_and_the_index(self):
        files = reference.plan(self.copy.root)
        nav = files["mkdocs.yml"].split("\n")
        i = nav.index("      - How to read a page: reference/reading.md")
        self.assertEqual(nav[i + 1], "      - C++ API: api/index.md")
        self.assertIn("The [C++ API](../api/index.md), which Doxygen generates", files["docs/reference/index.md"])

    def test_hand_written_pages_are_in_the_nav_and_kept(self):
        # The pages of PAGES are listed in the nav, in their group, and neither stray nor rewritten.
        ops = reference.load_operations(self.copy.root)
        self.assertIn(("construction", "Constants from fractions", "rational"), ops.PAGES)
        files = reference.plan(self.copy.root)
        nav = files["mkdocs.yml"].split("\n")
        group = nav.index("      - Construction and access:")
        line = nav.index("          - Constants from fractions: reference/rational.md")
        self.assertTrue(group < line < nav.index("      - Arithmetic:"))
        self.assertNotIn("docs/reference/rational.md", files)
        self.assertTrue(os.path.exists(self.copy.path("docs/reference/rational.md")))
        self.assertEqual(reference.check(self.copy.root), [])

    def test_crlf_checkout_is_fresh(self):
        for rel in ("docs/reference/add_2_2.md", "mkdocs.yml"):
            path = self.copy.path(rel)
            text = reference.read(path)
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(text.replace("\n", "\r\n"))
        self.assertEqual(reference.check(self.copy.root), [])

    def test_unverified_kernel_is_marked(self):
        data = self.copy.claims()
        self.copy.kernel(data, "add_2_1")["status"] = "unverified"
        self.copy.set_claims(data)
        files = reference.plan(self.copy.root)
        page = files["docs/reference/add_2_1.md"]
        self.assertIn("**UNVERIFIED: no proof is checked.**", page)
        self.assertIn("## Target (not proved)", page)
        self.assertNotIn("as compiled", page)
        index = files["docs/reference/index.md"]
        self.assertIn("[`add_2_1`](add_2_1.md) **UNVERIFIED**", index)

    def test_runs_that_judged_other_claims_are_flagged(self):
        data = self.copy.claims()
        self.copy.kernel(data, "mul_2_2")["ensures"][1]["c"] = "5"
        self.copy.set_claims(data)
        page = reference.plan(self.copy.root)["docs/reference/mul_2_2.md"]
        self.assertIn("These runs judged other claims", page)

    def test_runs_in_the_extended_domain_are_read_as_such(self):
        # The stored summaries record each series' domain: a full kernel's page says that the runs
        # judged it with infinite and NaN operands, and measures the entries of its core (F2).
        page = reference.plan(self.copy.root)["docs/reference/add_2_2_full.md"]
        self.assertIn("They judged the kernel in the extended domain, infinite and NaN operands included", page)
        self.assertIn("largest error / bound (core `add_2_2`)", page)
        self.assertNotIn("These runs judged other claims", page)
        self.assertNotIn("hold no measurement of the statement on infinite and NaN operands", page)

    def test_missing_theorem_fails(self):
        data = self.copy.claims()
        self.copy.kernel(data, "abs_2")["theorem"]["name"] = "abs_2_no_such_theorem"
        self.copy.set_claims(data)
        self.fails("abs_2", "abs_2_no_such_theorem")

    def edit_file(self, rel, edit):
        path = self.copy.path(rel)
        text = edit(reference.read(path))
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def test_axioms_come_from_the_allow_list(self):
        page = self.page("lt_2_2")
        self.assertIn("## Axioms", page)
        allowed, _ = reference.load_audit(self.copy.root)
        self.assertEqual(len(allowed), 4)
        for a in allowed:
            self.assertIn("- `%s`" % a, page)
        self.assertIn("one of the four listed in", page)
        self.assertIn("(`Print Assumptions lt_2_2_correct`, in [`proofs/gen/Audit.v`]", page)
        self.assertIn("(`Print Assumptions lt_2_2_ieee_correct`, in [`proofs/gen/IeeeAudit.v`]", page)
        self.assertIn("the proofs of `lt_2_2_correct` and `lt_2_2_ieee_correct` depend on", page)
        self.assertIn("the artifact `proof-audit` of each run of the [Proofs workflow](%s)" % reference.PROOFS_WORKFLOW,
                      page)
        self.assertIn("the proof of `add_2_2_full_correct` depends on", self.page("add_2_2_full"))
        # The list is read from the file, not written into the script.
        self.edit_file(reference.ALLOWED_AXIOMS, lambda t: t + "Some.new_axiom\n")
        page = self.page("lt_2_2")
        self.assertIn("one of the five listed in", page)
        self.assertIn("- `Some.new_axiom`", page)
        self.assertIn("finds none beyond the five allowed", page)

    def test_an_empty_allow_list_fails(self):
        self.edit_file(reference.ALLOWED_AXIOMS, lambda t: "\n".join(l for l in t.split("\n") if l.startswith("#")))
        self.fails(reference.ALLOWED_AXIOMS, "lists no axiom")

    def test_a_proved_theorem_that_no_audit_prints_fails(self):
        self.edit_file("proofs/gen/Audit.v", lambda t: t.replace("Print Assumptions add_2_1_correct.", ""))
        self.fails("add_2_1", "add_2_1_correct", "no audit file prints")

    def test_an_audit_line_in_a_comment_does_not_count(self):
        self.edit_file("proofs/gen/IeeeAudit.v", lambda t: t.replace(
            "Print Assumptions lt_2_2_ieee_correct.", "(* Print Assumptions lt_2_2_ieee_correct. *)"))
        self.fails("lt_2_2", "lt_2_2_ieee_correct", "no audit file prints")

    def test_no_axioms_without_a_proved_theorem(self):
        self.change("add_2_1", lambda k: k.update(status="unverified"))
        page = self.page("add_2_1")
        self.assertNotIn("## Axioms", page)
        self.assertNotIn("Print Assumptions", page)
        # An UNVERIFIED statement about infinite and NaN operands leaves only the other theorem.
        self.change("lt_2_2", lambda k: k.update(ieee_status="unverified"))
        page = self.page("lt_2_2")
        self.assertIn("the proof of `lt_2_2_correct` depends on", page)
        self.assertNotIn("Print Assumptions lt_2_2_ieee_correct", page)

    def test_no_brute_results(self):
        shutil.rmtree(self.copy.path("results"))
        page = reference.plan(self.copy.root)["docs/reference/add_2_2.md"]
        self.assertIn("No stored brute-force run has judged this kernel yet.", page)


class Numbers(unittest.TestCase):
    def test_exact_forms(self):
        F = reference.fractions.Fraction
        self.assertEqual(reference.exact_tex(F(1, 9007199254740993)), "\\frac{1}{2^{53} + 1}")
        self.assertEqual(reference.exact_tex(F(3, 81129638414606645666991986180096)), "\\frac{3}{2^{106} - 2^{55}}")
        self.assertEqual(reference.exact_tex(F(1, 93824969867264)), "\\frac{3}{2^{48} - 2^{26}}")
        self.assertEqual(reference.exact_tex(F(3, 2 ** 1075)), "3 \\cdot 2^{-1075}")
        self.assertEqual(reference.exact_tex(F(1, 2 ** 104)), "2^{-104}")

    def test_approximation(self):
        F = reference.fractions.Fraction
        self.assertEqual(reference.approx(F(1, 2 ** 1075)), "2.4703 \\times 10^{-324}")
        self.assertEqual(reference.approx(F(1, 2 ** 46)), "1.4211 \\times 10^{-14}")

    def test_expressions(self):
        self.assertEqual(reference.tex(reference.parse("3/(1-4*u)", "test", {"u"})), "\\frac{3}{1 - 4u}")
        self.assertEqual(reference.tex(reference.parse("x-(a-y)", "test", {"x", "a", "y"})), "x - (a - y)")
        self.assertEqual(reference.tex(reference.parse("cx*a", "test", {"cx", "a"})), "c_x a")
        self.assertEqual(reference.name_tex("cz0"), "c_{z0}")
        with self.assertRaises(reference.ReferenceError):
            reference.parse("x^2", "test", {"x"})
        with self.assertRaises(reference.ReferenceError):
            reference.parse("x+q", "test", {"x"})
        # The expressions of the claims of Milestone 2 (an upper bound's own value, holds): integer
        # powers and the constants of a kernel's bound, there only.
        with self.assertRaises(reference.ReferenceError):
            reference.parse("m*unit(add_2_2)", "test", {"m"})
        node = reference.parse("m*unit(add_2_2)/(1-m*unit(add_2_2))", "test", {"m"}, constants=True)
        self.assertEqual(reference.tex(node), "\\frac{m \\mathrm{unit}(\\mathtt{add\\_2\\_2})}"
                                              "{1 - m \\mathrm{unit}(\\mathtt{add\\_2\\_2})}")
        self.assertEqual(reference.tex(reference.parse("(1+u)^2*2^-3", "test", {"u"}, constants=True)),
                         "(1 + u)^{2} 2^{-3}")
        self.assertEqual(reference.name_tex("ok"), "\\mathit{ok}")
        self.assertEqual(reference.name_tex("flag"), "\\mathit{flag}")


if __name__ == "__main__":
    unittest.main(verbosity=1)
