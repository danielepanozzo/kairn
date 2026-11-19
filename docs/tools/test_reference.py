#!/usr/bin/env python3
"""The tests of docs/tools/reference.py and of its table, docs/tools/reference_operations.py.

  python3 docs/tools/test_reference.py      (ctest: docs.reference.test)

- The table against the data: every kernel it names is in gen/claims.json, and every public
  operation of include/kairn/*.hpp whose comment names a kernel (`(kernel add_2_2)`,
  `kernels sub_2_1 and sub_1_2`) is one of that kernel's forms, or of its traits entries.
- The tool on modified copies of its inputs: it fails, naming what it cannot print, on an unknown
  claim kind, requirement or status, on a kernel the table does not have, and on an extended
  kernel unless the switch says skip; --check fails on a stale, missing or stray page and on a
  stale nav; an UNVERIFIED kernel is marked; runs that judged other claims are flagged.

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
    for fname in ("expansion.hpp", "ball.hpp", "traits.hpp"):
        path = os.path.join(root, "include", "kairn", fname)
        lines = reference.read(path).split("\n")
        context, detail, comment = None, False, []
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if s.startswith("namespace detail {"):
                detail = True
            elif s.startswith("}  // namespace detail"):
                detail = False
            m = re.match(r"(?:struct|class) (Expansion<T, [12]>|Ball|traits_one_limb|traits<Expansion<T, 2>>) \{", s)
            if m:
                context = {"Ball": "Ball<T, K>", "traits_one_limb": "traits<T>"}.get(m.group(1), m.group(1))
                comment = []
                continue
            if s == "};":
                context = None
            if s.startswith("///"):
                comment.append(s[3:].strip())
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
            f = re.search(r"(operator(?:\+=|-=|\*=|==|!=|<=|>=|[-+*<>])|\b[A-Za-z_]\w*)\(([^)]*)\)", s)
            if not f:
                raise AssertionError("%s: cannot read the declaration %r" % (where, s))
            name = f.group(1)
            if context and name == context.split("<")[0]:
                name = context                                   # a constructor
            operands = tuple(param_type(p, context) for p in split_params(f.group(2)))
            found.append((where, ("op", name, operands), names))
    return found


def form_key(f):
    code = f["code"]
    m = re.fullmatch(r"(\w+) (\+=|-=|\*=|==|!=|<=|>=|[-+*<>]) (\w+)", code)
    if m:
        return ("op", "operator" + m.group(2), tuple(f["operands"]))
    m = re.fullmatch(r"-(\w+)", code)
    if m:
        return ("op", "operator-", tuple(f["operands"]))
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
        missing = [k for k, e in self.claims.items()
                   if e.get("domain", "finite") == "finite" and k not in self.ops.KERNELS]
        self.assertEqual(missing, [], "kernels of gen/claims.json that the table does not have")

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
        self.assertIn((("op", "operator+", ("Expansion<T, 2>", "Expansion<T, 2>")), ("add_2_2",)), keys)
        self.assertIn((("op", "Expansion<T, 1>", ("Expansion<T, 2>",)), ("to_nearest_2",)), keys)
        self.assertIn((("op", "operator+", ("Ball<T, K>", "Ball<T, K>")), ("ball_add_1", "ball_add_2")), keys)
        self.assertIn((("traits", "traits<Expansion<T, 2>>::sub_limb"), ("sub_2_1", "sub_1_2")), keys)


# --- The tool on modified copies ---------------------------------------------------------------

COPIED = ["gen/claims.json", "gen/kernels", "include/kairn/gen/bounds.hpp", "results",
          "docs/tools/reference_operations.py", "docs/developer/design/phase0/references.md",
          "docs/developer/results", "proofs/theories", "proofs/gen/Statements.v", "mkdocs.yml",
          "docs/reference"]


class Copy:
    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="kairn-reference-")
        for rel in COPIED:
            src, dst = os.path.join(ROOT, rel), os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy(src, dst)

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

    def fails(self, *words, extended="fail"):
        with self.assertRaises(reference.ReferenceError) as ctx:
            reference.plan(self.copy.root, extended)
        for w in words:
            self.assertIn(w, str(ctx.exception))
        return str(ctx.exception)

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
        data = self.copy.claims()
        self.copy.kernel(data, "neg_2")["ieee_status"] = "proved"
        self.copy.set_claims(data)
        self.fails("neg_2", "ieee_status")

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

    def extended_kernel(self):
        data = self.copy.claims()
        data["kernels"].append({
            "name": "add_2_1_full", "domain": "extended",
            "inputs": [{"name": "x", "limbs": 2}, {"name": "a", "limbs": 1}],
            "outputs": [{"name": "w", "limbs": 2}], "value": "x+a", "requires": ["canonical(x)"],
            "ensures": [{"kind": "extends", "of": "w", "core": "add_2_1", "lead": "add", "finite_when": []}],
            "min_precision": 3, "status": "unverified", "ieee_status": "unverified",
            "instances": {"binary64": [], "binary32": []}})
        self.copy.set_claims(data)

    def test_extended_kernel_fails_by_default(self):
        self.extended_kernel()
        self.assertEqual(reference.EXTENDED_DOMAIN, "fail", "the switch's committed value is fail")
        self.fails("add_2_1_full", "EXTENDED_DOMAIN")

    def test_extended_kernel_skipped_on_request(self):
        self.extended_kernel()
        files = reference.plan(self.copy.root, "skip")
        self.assertNotIn("docs/reference/add_2_1_full.md", files)
        index = files["docs/reference/index.md"]
        self.assertIn("## Not in this reference yet", index)
        self.assertIn("`add_2_1_full`", index)

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

    def test_missing_theorem_fails(self):
        data = self.copy.claims()
        self.copy.kernel(data, "abs_2")["theorem"]["name"] = "abs_2_no_such_theorem"
        self.copy.set_claims(data)
        self.fails("abs_2", "abs_2_no_such_theorem")

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


if __name__ == "__main__":
    unittest.main(verbosity=1)
