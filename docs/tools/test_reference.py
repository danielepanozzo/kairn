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
- The stored brute-force runs a page counts: those of every campaign whose code is the kernel's
  now; none after its code changed in place, or after a kernel it calls changed (printed again by
  the generator) or a function of the prelude it calls; all of them after a change of a text field,
  a comment or the indentation; a kernel no run judged says so; the total of several campaigns
  leaves out the runs that judged other claims and counts a toy domain once; a summary of a commit
  that results/brute-code.json does not have fails.
- docs/tools/brute_code.py, on headers written for the test: what a definition is, which changes
  are of code, what it refuses to read, which fields of a claims entry are claims;
  results/brute-code.json has every commit of the stored runs, and is what the history gives
  (where the history is in the clone: a shallow one skips it).
- Claims, on the tree: for every kernel and every stored summary of its code, the page says that the
  runs judged other claims exactly where the claims of the summary's commit are not the claims
  now, and the oracle's recorded label of every entry is the one the page prints for that claim
  wherever they are the same (the old printing of the Milestone 2 kinds fails it); a change of the
  claims that the labels do not show is said as such.

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
    # The set operand of contains(Y), a template on its number of limbs J so that no point converts
    # to a set, which the constraint J == K makes the class's own K.
    t = t.replace("<T, J>", "<T, K>")
    if t == "Expansion" and context and context.startswith("Expansion<"):
        return context
    if t == "Ball":
        return "Ball<T, K>"
    if t == "Interval":
        return "Interval<T, K>"
    return t


# kairn/upward.hpp, the round-up interval: there Interval is kairn::upward::Interval<T>, which the
# table writes upward::Interval<T>, View<T> and View<const T> are the views of its functions on
# arrays, and ::kairn::Interval<T, 1> is the default interval.
UPWARD_TYPES = {"Interval": "upward::Interval<T>", "Interval<T>": "upward::Interval<T>",
                "Interval<U>": "upward::Interval<T>", "View<T>": "upward::View<T>",
                "View<const T>": "upward::View<const T>", "::kairn::Interval<T, 1>": "Interval<T, 1>"}


def upward_param_type(param):
    """The type of a parameter of kairn/upward.hpp, as the table writes it (UPWARD_TYPES); a view
    read keeps its const, which param_type would drop."""
    t = re.sub(r"&", " ", param).strip()
    t = re.sub(r"\s+[A-Za-z_]\w*\s*$", "", t)            # the parameter's name
    t = re.sub(r"\s+", " ", re.sub(r"^const\s+", "", t.strip())).strip()
    m = re.fullmatch(r"std::type_identity_t<(.*)>", t)
    if m:
        t = m.group(1)
    return UPWARD_TYPES.get(t, t)


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
    for fname in ("expansion.hpp", "ball.hpp", "interval.hpp", "traits.hpp", "blocks.hpp", "upward.hpp"):
        upward = fname == "upward.hpp"
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
            elif s.startswith("namespace ieee1788 {"):
                prefix = "ieee1788::"                            # kairn::ieee1788::subset(X, Y)
            elif s.startswith("}  // namespace finite") or s.startswith("}  // namespace ieee1788"):
                prefix = ""
            m = re.match(r"(?:struct|class) (Expansion<T, [12]>|Ball|Interval|traits_one_limb|traits<Expansion<T, 2>>) \{",
                         s)
            if m:
                context = {"Ball": "Ball<T, K>", "Interval": "upward::Interval<T>" if upward else "Interval<T, K>",
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
            if context and name == context.split("<")[0].split("::")[-1]:
                name = context                                   # a constructor
            elif not context:
                name = prefix + name
            operands = tuple(upward_param_type(p) if upward else param_type(p, context)
                             for p in split_params(f.group(2)))
            found.append((where, ("op", name, operands), names))
    return found


def header_kernel_uses(root, known):
    """(named, called): the kernels the /// comments of the public headers name for an operation,
    and those the headers call as kairn::gen functions or gate on (gen::bounds::K)."""
    named = set()
    for _, _, names in header_operations(root, known):
        named |= set(names)
    called = set()
    # The kernels of the loops the headers call (gen::F_seq, F_lanes, F_packed) or gate on
    # (gen::bounds::loops::F, through the alias loops::F): a step, a combination, a check or a
    # finish is reached through its loop, and so are the kernels of a loop's coefficients.
    with open(os.path.join(root, "gen", "claims.json"), encoding="utf-8") as f:
        folds = {fd["name"]: fd for fd in json.load(f).get("folds", [])}

    def loop_kernels(name):
        fd = folds[name]
        out = {fd[k] for k in ("step", "combine", "finish", "check") if isinstance(fd.get(k), str)} & known
        return out | (loop_kernels(fd["coefficients"]) if fd.get("coefficients") in folds else set())

    d = os.path.join(root, "include", "kairn")
    for fname in os.listdir(d):
        if fname.endswith(".hpp"):
            text = reference.read(os.path.join(d, fname))
            called |= set(re.findall(r"\bgen::(\w+)\(", text)) & known
            called |= set(re.findall(r"\bgen::bounds::(\w+)<", text)) & known
            loops = {m for m in re.findall(r"\bgen::(\w+)_(?:seq|lanes|packed)\(", text) if m in folds}
            loops |= {m for m in re.findall(r"\bloops::(\w+)<", text) if m in folds}
            for name in loops:
                called |= loop_kernels(name)
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
        # A kernel that a loop of reference_operations.LOOPS names (the loops of kairn/ball_vector.hpp,
        # whose steps the program's arrays enter, bv_center_entry_1 among them) has a page that says
        # which loop and which operations call it: not "no header calls it".
        parts = {n for loop in getattr(self.ops, "LOOPS", {}) for n in reference.fold_kernels(ROOT, loop)}
        self.assertIn("bv_center_entry_1", parts)
        used = [k for k in entry if k in named | called and k not in parts]
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
        self.assertIn((("op", "Ball<T, K>", ("Expansion<T, K>", "T")), ("ball_make_1", "ball_make_2_entry")), keys)
        self.assertIn((("op", "two_sum", ("T", "T")), ("two_sum_entry",)), keys)
        self.assertIn((("op", "certainly_positive", ()), ("ball_positive_1", "ball_positive_2")), keys)
        self.assertIn((("op", "certainly_positive", ()), ("interval_positive_1", "interval_positive_2")), keys)
        self.assertIn((("op", "Ball<T, K>", ("Constant<Expansion<T, K>>",)), ("ball_make_1", "ball_make_2_entry")), keys)
        self.assertIn((("traits", "traits<Expansion<T, 2>>::sub_limb"), ("sub_2_1", "sub_1_2")), keys)
        # Intervals, and the functions of a Ball of the interface the two share.
        self.assertIn((("op", "operator*", ("Interval<T, K>", "Interval<T, K>")), ("interval_mul_1", "interval_mul_2")),
                      keys)
        self.assertIn((("op", "Interval<T, K>", ("Expansion<T, K>", "Expansion<T, K>")),
                       ("interval_make_1", "interval_make_2_entry")), keys)
        self.assertIn((("op", "hull", ("Interval<T, K>",)), ("interval_hull_1", "interval_hull_2")), keys)
        self.assertIn((("op", "split", ()), ("interval_split_1", "interval_split_2")), keys)
        self.assertIn((("op", "lower_as", ()), ("to_down_2",)), keys)
        self.assertIn((("op", "lower_as", ()), ("ball_lower_as_1", "ball_lower_as_2")), keys)
        self.assertIn((("op", "Ball<T, K>", ("Interval<T, K>",)), ("interval_to_ball_1", "interval_to_ball_2")), keys)
        self.assertIn((("op", "Ball<T, K>", ("Ball<T, 2>",)), ("ball_narrow_2_1",)), keys)
        self.assertIn((("op", "from_interval", ("T", "T")), ("ball_from_interval_1", "ball_from_interval_2")), keys)
        # The enclosure interface of stage B2: a set operand of contains, a template on its limbs; the
        # free functions of three-valued answers; the relations of IEEE 1788 under their namespace.
        self.assertIn((("op", "contains", ("Interval<T, K>",)), ("interval_subset_1", "interval_subset_2")), keys)
        self.assertIn((("op", "contains", ("Ball<T, K>",)), ("ball_contains_ball_1", "ball_contains_ball_2")), keys)
        self.assertIn((("op", "less", ("Ball<T, K>", "Ball<T, K>")), ("ball_less_1", "ball_less_2")), keys)
        self.assertIn((("op", "member", ("T", "Interval<T, K>")), ("interval_contains_1", "interval_contains_2")), keys)
        self.assertIn((("op", "ieee1788::subset", ("Interval<T, K>", "Interval<T, K>")),
                       ("interval_subset_1", "interval_subset_2")), keys)
        self.assertIn((("op", "lower", ()), ("ball_lower_as_1", "ball_to_interval_2")), keys)
        # The round-up interval (kairn/upward.hpp): Interval there is kairn::upward::Interval<T>, a
        # number may be either operand, a composition names both kernels, a view read keeps its
        # const, and the conversion from the default interval is a constructor.
        U, UW, UR = "upward::Interval<T>", "upward::View<T>", "upward::View<const T>"
        self.assertIn((("op", "operator*", (U, U)), ("upward_mul_1",)), keys)
        self.assertIn((("op", "operator+", ("T", U)), ("upward_add_num_1",)), keys)
        self.assertIn((("op", "operator-", ("T", U)), ("upward_add_num_1", "upward_neg_1")), keys)
        self.assertIn((("op", "operator-=", (U, "T")), ("upward_add_num_1",)), keys)
        self.assertIn((("op", U, ("T", "T")), ("upward_make_1",)), keys)
        self.assertIn((("op", U, ("Interval<T, 1>",)), ("upward_from_interval_1",)), keys)
        self.assertIn((("op", "to_interval", ()), ("upward_to_interval_1",)), keys)
        self.assertIn((("op", "contains", (U,)), ("upward_subset_1",)), keys)
        self.assertIn((("op", "member", ("T", U)), ("upward_contains_1",)), keys)
        self.assertIn((("op", "ieee1788::interior", (U, U)), ("upward_rel_interior_1",)), keys)
        self.assertIn((("op", "add", (UW, UR, UR)), ("upward_add_1",)), keys)
        self.assertIn((("op", "mul", (UW, UR, "T")), ("upward_mul_num_1",)), keys)


# --- The tool on modified copies ---------------------------------------------------------------

COPIED = ["gen/claims.json", "gen/kernels", "include/kairn/gen/bounds.hpp", "include/kairn/gen/prelude.hpp",
          "include/kairn/gen/scalar.hpp", "include/kairn/gen/avx2.hpp", "include/kairn/gen/neon.hpp", "results",
          "docs/tools/reference_operations.py", "docs/developer/design/phase0/references.md",
          "docs/developer/results", "proofs/theories", "proofs/gen/Statements.v", "proofs/gen/Model.v",
          "proofs/gen/IeeeModel.v", "proofs/gen/Audit.v", "proofs/gen/IeeeAudit.v", "proofs/audit",
          "proofs/gen/UpwardModel.v", "proofs/gen/UpwardStatements.v", "proofs/gen/UpwardAudit.v",
          "mkdocs.yml",
          "docs/reference"]
# Inputs that a tree may not have yet: the C++ of the round-up interval, which its pages say is not
# printed while the file is not there.
COPIED_IF_PRESENT = ["include/kairn/gen/upward.hpp"]


def edit_definitions(text, name, old, new):
    """A generated header with old replaced by new in the definitions of the function name (from the
    line that names it to the next line that is a closing brace alone)."""
    lines, inside, done = text.split("\n"), False, 0
    for i, line in enumerate(lines):
        if not inside and re.search(r"[ *&]%s\(.*\{$" % re.escape(name), line) and not line.startswith(" "):
            inside = True
        if inside:
            if old in line:
                lines[i] = line.replace(old, new)
                done += 1
            if line == "}":
                inside = False
    if not done:
        raise AssertionError("no definition of %s has %r" % (name, old))
    return "\n".join(lines)


def print_headers(root):
    """Print include/kairn/gen/prelude.hpp, scalar.hpp, avx2.hpp and neon.hpp under root from the
    descriptions of root/gen/kernels/, with the repository's generator, as `kairn-gen build` would."""
    sys.path.insert(0, os.path.join(ROOT, "gen"))
    keep = sys.dont_write_bytecode
    sys.dont_write_bytecode = True   # as gen/kairn-gen: nothing of a run is written into the repository
    try:
        from kairn_gen import build, cpp, simd
    finally:
        sys.dont_write_bytecode = keep
        sys.path.pop(0)
    kernels, errors = build.load(root)
    if errors:
        raise AssertionError("the generator refuses the descriptions: %s" % errors)
    for name, text in (("prelude", cpp.prelude(kernels)), ("scalar", cpp.scalar(kernels)),
                       ("avx2", simd.header(simd.AVX2, kernels)), ("neon", simd.header(simd.NEON, kernels))):
        with open(os.path.join(root, "include", "kairn", "gen", name + ".hpp"), "w", encoding="utf-8",
                  newline="\n") as f:
            f.write(text)


def table_rows(text, lead):
    """{title: (cases judged, failed)} of the table after the paragraph that starts with lead."""
    after = text[text.index(lead):]
    rows = {}
    for line in after.split("\n")[1:]:
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells[0] in ("Run", "---"):
            continue
        rows[cells[0]] = (int(cells[1].replace(" ", "")), int(cells[2].replace(" ", "")))
    return rows


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
        for rel in COPIED + [r for r in COPIED_IF_PRESENT if os.path.exists(os.path.join(ROOT, r))]:
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

    # The round-up interval (architecture.md, "Claims of the round-up interval"): its pages are
    # printed whatever the statuses are, so each test sets the ones it reads.
    def unverified(self, name):
        self.change(name, lambda k: (k.update(status="unverified", ieee_status="unverified"),
                                     k.pop("ieee_theorem", None)))

    def test_upward_kernels(self):
        # A stored pair, its requirement and the state of a result; I4 of a product, exactly rounded,
        # in both lanes upward; the listing's operations and pair lines; what is assumed.
        page = self.page("upward_mul_1")
        self.assertIn("- $X = [-x_n, x_u]$, stored as $(x_u, x_n)$, is a canonical state of the round-up interval: "
                      "the empty set, both lanes a NaN; or a nonempty interval", page)
        self.assertIn("**I1.** The result $Z = [-z_n, z_u]$, stored as $(z_u, z_n)$, is a canonical state", page)
        self.assertIn("$-z_n = \\mathrm{RD}(\\ell)$ and $z_u = \\mathrm{RU}(h)$, the roundings in the format with "
                      "overflow", page)
        self.assertIn("both lanes rounded upward, $z_n = \\mathrm{RU}(-\\ell)$", page)
        self.assertNotIn("step of `T`", page)
        self.assertIn("Its products round upward, toward $+\\infty$", page)
        self.assertIn("its products rounded upward, toward $+\\infty$, with gradual underflow, in the IEEE model", page)
        self.assertIn("A line of two statements separated by ` | ` is a *pair line*", page)
        self.assertIn("`max_nl(a, b)` is the greater of $a$ and $b$, and $b$ when $a$ is a NaN", page)
        self.assertNotIn("prod(a, b)", page)
        self.assertIn("$X$ as $(x_u, x_n)$, $Y$ as $(y_u, y_n)$, $Z$ as $(z_u, z_n)$", page)
        self.assertIn("its products rounded upward, and no flush to zero of results or operands", page)
        self.assertIn("(`proofs/gen/UpwardModel.v`)", page)
        # The C++ of the family: its forms, its namespace and header, and its views of arrays.
        self.assertIn("| `X * Y` | `upward::Interval<T>`, `upward::Interval<T>` | `upward::Interval<T>` |", page)
        self.assertIn("| `mul(z, x, y)` | `upward::View<T>`, `upward::View<const T>`, `upward::View<const T>` | "
                      "`void` |", page)
        self.assertIn("The operations are in namespace `kairn::upward`, header `kairn/upward.hpp`", page)
        self.assertIn("an operation that rounds runs only inside an upward scope (a function on arrays holds its "
                      "own)", page)
        self.assertNotIn("header `kairn/kairn.hpp`. The operators", page)
        page = self.page("upward_hull_1")
        self.assertIn("`upward::Interval<T>` is the round-up interval `kairn::upward::Interval<T>`, and "
                      "`Interval<T, 1>` the default", page)
        self.assertNotIn("views of two arrays", page)
        # A number: the members of Interval(t), and I5 for a finite one.
        page = self.page("upward_add_num_1")
        self.assertIn("$Z$ contains $x + t'$ for every $x \\in X$, $t' \\in \\langle t\\rangle$", page)
        self.assertIn("$\\langle t\\rangle$ is the set of the number $t$ as `Interval(t)` makes it", page)
        self.assertIn("**I5.** For bounded $X$ and a finite $t$, $Z$ is bounded exactly when", page)
        self.assertIn("- $t$ is any value of `T`: a number, $\\pm\\infty$ or a NaN.", page)
        self.assertIn("Its sums round upward", page)
        # The conversions (same_set), the constructor, the set operations, a predicate.
        page = self.page("upward_to_interval_1")
        self.assertIn("$Z$ is the empty set, $(+\\infty, -\\infty)$, exactly when $X$ is empty.", page)
        self.assertIn("so for a nonempty $X$ the same bounds, $z_l = -x_n$ and $z_u = x_u$, exactly", page)
        self.assertIn("The result $Z = [z_l, z_u]$ is a canonical interval.", page)
        page = self.page("upward_from_interval_1")
        self.assertIn("- $X = [x_l, x_u]$ is a canonical interval", page)
        self.assertIn("$Z$ is the empty set, both lanes a NaN, exactly when $X$ is empty.", page)
        self.assertIn("$-z_n = x_l$ and $z_u = x_u$", page)
        page = self.page("upward_make_1")
        self.assertIn("$Z$ is the whole line, $(z_u, z_n) = (+\\infty, +\\infty)$.", page)
        self.assertIn("$Z$ is the empty set, both lanes a NaN.", page)
        self.assertIn("$-z_n = l_o$ and $z_u = h_i$", page)
        self.assertIn("$\\min(-x_n, -y_n)$ and $\\max(x_u, y_u)$", self.page("upward_hull_1"))
        self.assertIn("$-z_n = \\max(-x_n, -y_n)$ and $z_u = \\min(x_u, y_u)$", self.page("upward_intersection_1"))
        page = self.page("upward_less_1")
        self.assertIn("$X = [-x_n, x_u]$ and $Y = [-y_n, y_u]$", page)
        self.assertIn("No operation of it rounds: it gives the same result in every rounding mode.", page)
        self.assertIn("at least 1 bit, no operation of the kernel rounding, in the IEEE model", page)
        self.assertIn("no flush to zero of results or operands (its result does not depend on the rounding mode)", page)
        # The index: the group of the family, and its page in the nav after the kernels.
        files = reference.plan(self.copy.root)
        self.assertIn("## The round-up interval\n", files["docs/reference/index.md"])
        nav = files["mkdocs.yml"].split("\n")
        self.assertLess(nav.index("          - The negation of a round-up interval: reference/upward_neg_1.md"),
                        nav.index('          - "The round-up interval: its kernels": reference/upward.md'))

    def test_upward_statuses(self):
        # UNVERIFIED: the statement in UpwardStatements.v, and the sentence on hand-written proofs.
        self.unverified("upward_add_1")
        page = self.page("upward_add_1")
        self.assertIn("**UNVERIFIED.** No proof of the statement is checked. The statement is `upward_add_1_spec`, "
                      "which the generator prints from these claims into [`proofs/gen/UpwardStatements.v`]", page)
        self.assertIn(reference.IEEE_PROOFS_SENTENCE, page)
        self.assertIn("[`upward_add_1`](upward_add_1.md) **UNVERIFIED**", self.page("index"))
        # Proved: the theorem, its file and the audit of the family, and the axioms.
        self.edit_file("proofs/theories/IeeeUpwardOps.v",
                       lambda t: t + "\n(* A test. *)\nTheorem upward_add_1_test_correct : True.\nProof. exact I. Qed.\n")
        self.change("upward_add_1", lambda k: k.update(status="proved", ieee_status="proved", ieee_theorem={
            "file": "proofs/theories/IeeeUpwardOps.v", "name": "upward_add_1_test_correct"}))
        self.fails("upward_add_1", "upward_add_1_test_correct", "no audit file prints")
        self.edit_file("proofs/gen/UpwardAudit.v", lambda t: t + "Print Assumptions upward_add_1_test_correct.\n")
        page = self.page("upward_add_1")
        self.assertIn("Kernel `upward_add_1` · proved ·", page)
        self.assertIn("## Guarantees", page)
        self.assertIn("**Proved.** Rocq checks the theorem `upward_add_1_test_correct`, in "
                      "[`proofs/theories/IeeeUpwardOps.v`]", page)
        self.assertIn(", against `upward_add_1_spec`, the statement the generator prints from these claims into "
                      "[`proofs/gen/UpwardStatements.v`]", page)
        self.assertIn("(`Print Assumptions upward_add_1_test_correct`, in [`proofs/gen/UpwardAudit.v`]", page)
        self.assertIn("## Axioms", page)
        self.assertNotIn(reference.IEEE_PROOFS_SENTENCE, page)
        # A kernel of the family that UpwardStatements.v does not state fails.
        self.edit_file(reference.UPWARD_STATEMENTS, lambda t: t.replace("Definition upward_sub_1_spec", "Definition x_spec"))
        self.fails("upward_sub_1", "UpwardStatements.v", "upward_sub_1_spec")

    def test_upward_cpp_when_printed(self):
        # The C++ of the family: named on a page once include/kairn/gen/upward.hpp defines the kernel.
        path = self.copy.path(reference.UPWARD_CPP)
        if os.path.exists(path):
            os.remove(path)
        self.assertIn("The generator prints no C++ of it yet.", self.page("upward_neg_1"))
        with open(path, "w", encoding="utf-8") as f:
            f.write("inline void upward_neg_1() {}\n")
        page = self.page("upward_neg_1")
        self.assertIn("the description the C++ (`include/kairn/gen/upward.hpp`) and the formal model "
                      "(`proofs/gen/UpwardModel.v`) are generated from", page)
        self.assertNotIn("prints no C++", page)

    def test_upward_vocabulary_only_in_the_family(self):
        # The requirement upward(), stored pairs, numbers and same_set are read for the kernels that
        # say "rounding": "upward", and nowhere else; and the rounding is one the script knows.
        self.change("upward_add_1", lambda k: k.pop("rounding"))
        self.fails("upward_add_1", "upward(xu, xn)", "round-up interval")
        self.change("upward_add_1", lambda k: k.update(rounding="downward"))
        self.fails("upward_add_1", "downward")
        self.change("upward_add_1", lambda k: k.update(rounding="upward"))
        self.change("add_2_2", lambda k: k.update(rounding="upward"))
        self.fails("add_2_2", "extended domain and ieee_only")
        self.change("add_2_2", lambda k: k.pop("rounding"))
        self.change("interval_add_1", lambda k: k["ensures"][0].update(numbers=["xl"]))
        self.fails("interval_add_1", "numbers")
        self.change("interval_add_1", lambda k: k["ensures"][0].pop("numbers"))
        self.change("interval_make_1", lambda k: k.update(ensures=[
            {"kind": "same_set", "of": {"lower": "zl", "upper": "zu"}, "from": {"lower": "lo", "upper": "hi"}}]))
        self.fails("interval_make_1", "same_set", "round-up interval")

    def test_upward_sets(self):
        # A set of the family is its bounds or a stored pair that an upward() requirement names.
        self.change("upward_add_1", lambda k: k["ensures"][0]["intervals"].update(x={"upper": "xu", "nlower": "yn"}))
        self.fails("upward_add_1", "(xu, yn)", "upward()")
        self.change("upward_add_1", lambda k: k["ensures"][0]["intervals"].update(x={"top": "xu", "nlower": "xn"}))
        self.fails("upward_add_1", "neither its bounds")
        self.change("upward_add_1", lambda k: k["ensures"][0]["intervals"].update(x={"upper": "xu", "nlower": "xn"}))
        self.change("upward_to_interval_1", lambda k: k["ensures"][0].update(of={"upper": "zl", "nlower": "xu"}))
        self.fails("upward_to_interval_1", "same_set", "not an output")

    def test_labels_of_the_round_up_interval(self):
        # The oracle's labels (oracle/kairn_oracle/upward.py, set_text; intervals.py, _iv_text and
        # _outs_text), from the claims alone.
        label = reference.entry_label
        pair = {"x": {"upper": "xu", "nlower": "xn"}, "y": {"upper": "yu", "nlower": "yn"}}
        self.assertEqual(label({"kind": "same_set", "of": {"upper": "zu", "nlower": "zn"},
                                "from": {"lower": "xl", "upper": "xu"}}), "same_set((upper zu, nlower zn)) as [xl, xu]")
        self.assertEqual(label({"kind": "interval_set", "upper": "zu", "nlower": "zn", "set": "union", "intervals": pair}),
                         "interval_set(upper zu, nlower zn) union of x=(upper xu, nlower xn), y=(upper yu, nlower yn)")
        self.assertEqual(label({"kind": "makes_interval", "upper": "zu", "nlower": "zn",
                                "from": {"lower": "lo", "upper": "hi"}}),
                         "makes_interval(upper zu, nlower zn) from lower lo, upper hi")
        self.assertEqual(label({"kind": "certain", "of": "m", "rel": "empty", "args": ["x"],
                                "intervals": {"x": pair["x"]}, "exact": True}),
                         "certain(m) empty(x) over x=(upper xu, nlower xn), exact")
        self.assertEqual(label({"kind": "encloses_interval", "upper": "zu", "nlower": "zn", "set": "x+y",
                                "intervals": pair, "tight": {"kind": "rounded"}, "bounded_when": []}),
                         "encloses_interval(upper zu, nlower zn)")

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
        # The generated headers too: their line ends are not code.
        for rel in ("docs/reference/add_2_2.md", "mkdocs.yml", "include/kairn/gen/scalar.hpp"):
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
        self.assertIn("They judged `normalized(z)`; `error(z) form R, c=4, k=2, t=3/2`; the kernel now claims "
                      "`normalized(z)`; `error(z) form R, c=5, k=2, t=3/2`.", page)
        self.assertNotIn("**In all**", page)   # no run of either campaign judged the claims now

    def test_claims_changed_where_the_labels_do_not_show(self):
        # A smallest precision changed: the oracle's labels of the entries are the same, the claims
        # are not, and the page says so rather than call them the same.
        self.change("add_1_1", lambda k: k.update(min_precision=k["min_precision"] + 1))
        m = self.page("add_1_1")
        self.assertEqual(m.count("**These runs judged other claims.**"), 2)
        self.assertIn("They judged the claims of commits `6f89054` and `f7e0b6d`, which differ from the claims now "
                      "in what their labels do not show", m)
        # A text field is not a claim.
        self.change("add_2_2", lambda k: k.update(source={"cite": "elsewhere", "license": "MIT"}))
        self.assertNotIn("other claims", self.page("add_2_2"))

    def test_labels_of_the_kinds_of_milestone_2(self):
        # The oracle's labels of the kinds the summaries of Milestone 2 hold, from the claims alone.
        label = reference.entry_label
        self.assertEqual(label({"kind": "rounded", "of": "b", "mode": "nearest", "value": "a+abs(x[0])"}),
                         "rounded(b) nearest of a+abs(x[0])")
        self.assertEqual(label({"kind": "maximum", "of": "r", "args": ["m", "abs(x)"]}), "maximum(r) of m, abs(x)")
        self.assertEqual(label({"kind": "holds", "rel": "le", "args": ["m*u", "1/2"], "if": "ok"}),
                         "holds le(m*u, 1/2) if ok")
        self.assertEqual(label({"kind": "upper", "of": "r", "value": "g+t", "if": "ok"}), "upper(r) >= g+t if ok")
        self.assertEqual(label({"kind": "upper", "of": "rz", "value": "rx*c", "exact_when": [
            {"mask": "ex"}, {"zero_or_abs_gt": "rx*c", "than": "eta/(2*u)"}]}),
            "upper(rz) >= rx*c, exactly when ex true and (rx*c = 0 or |rx*c| > eta/(2*u))")
        self.assertEqual(label({"kind": "upper", "of": "rz", "value": "rx*c+eta", "unless": "ex"}),
                         "upper(rz) >= rx*c+eta unless ex")
        self.assertEqual(label({"kind": "outward", "of": "l", "side": "below", "rel": "u", "abs": "eta",
                                "exact_when": [{"zero": "x+y"}]}), "outward(l) below, exact when (x+y = 0)")
        self.assertEqual(label({"kind": "error", "of": "z", "form": "R", "c": "0", "k": 1, "t": "1/2", "when": None,
                                "exact_when": [{"zero_or_abs_gt": "x*c", "than": "eta/(2*u)"}], "exact_flag": "e"}),
                         "error(z) form R, c=0, k=1, t=1/2, exact when (x*c = 0 or |x*c| > eta/(2*u)), exact_flag e")

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

    # --- The stored runs of a kernel's code (results/brute-code.json, docs/tools/brute_code.py) ---

    def measured(self, name):
        page = self.page(name)
        return page[page.index("## Measured"):page.index("## Not claimed")]

    def test_unchanged_code_shows_the_runs_of_every_campaign(self):
        # add_1_1 has the code of Milestone 1's runs: its page shows them, those of Milestone 2, and
        # their total.
        m = self.measured("add_1_1")
        self.assertIn("**Milestone 1**: the runs of commit `6f89054`", m)
        self.assertIn("**Milestone 2**: the runs of commit `5f597fb`", m)
        self.assertNotIn("other code", m)
        self.assertIn("results/brute-code.json", m)
        # Milestone 1's runs as the summaries count them, and the total the sum of the campaigns.
        judged = sum(json.loads(reference.read(self.copy.path("results/milestone1/brute/" + f)))
                     ["compiled"]["kernels"]["add_1_1"]["binary64"]["counts"]["judged"]
                     for f in ("linux-x86-64.json", "macos-arm64.json", "windows-x64.json"))
        m1 = table_rows(m, "**Milestone 1**")
        m2 = table_rows(m, "**Milestone 2**")
        total = table_rows(m, "**In all**")
        title = "`binary64` (`double`), compiled"
        self.assertEqual(m1[title + ": 60 runners on 3 machines"][0], judged)
        self.assertGreater(judged, 10 ** 8)
        self.assertEqual(total[title + ", Milestone 1 and Milestone 2"][0],
                         judged + m2[title + ": 90 runners on 3 machines"][0])
        # An enumeration of a toy domain that an earlier one enumerated is counted once.
        toy = [t for t in total if t.startswith("toy formats")]
        self.assertEqual(len(toy), 1)
        self.assertIn("each counted once", toy[0])
        self.assertLess(total[toy[0]][0], sum(v[0] for t, v in list(m1.items()) + list(m2.items())
                                              if t.startswith("toy formats")))

    def test_code_changed_in_place_counts_no_run(self):
        # add_1_1's packed code changed after every stored run: no run is of its code, and the page
        # names the runs it does not count; a kernel whose code did not change keeps its runs.
        self.edit_file("include/kairn/gen/avx2.hpp",
                       lambda t: edit_definitions(t, "add_1_1", "_mm256_add_pd(a, b)", "_mm256_add_pd(b, a)"))
        m = self.measured("add_1_1")
        self.assertIn("No stored brute-force run is of this kernel's code as it is now: the runs of Milestone 1, "
                      "at commits `6f89054` and `f7e0b6d`, and of Milestone 2, at commit `5f597fb`, were of other "
                      "code, and are not counted.", m)
        self.assertNotIn("| Run |", m)
        self.assertIn("**Milestone 1**", self.measured("add_2_2"))

    def test_code_changed_since_a_campaign_shows_the_later_runs(self):
        # mul_1_1's code changed between Milestone 1 and Milestone 2 (its constant-evaluation branch):
        # its page shows the runs of Milestone 2 only, and says why.
        m = self.measured("mul_1_1")
        self.assertIn("**Milestone 2**", m)
        self.assertNotIn("**Milestone 1**", m)
        self.assertNotIn("**In all**", m)
        self.assertIn("The runs of Milestone 1, at commits `6f89054` and `f7e0b6d`, were of other code, and are "
                      "not counted.", m)
        # axpy_entry_step_2 was changed in place at the close of rule R3: only the supplementary run
        # of that commit is of its code.
        m = self.measured("axpy_entry_step_2")
        self.assertIn("**Milestone 2**: the supplementary run of commit `8ee5ed9`", m)
        self.assertIn("The runs of Milestone 2, at commit `5f597fb`, were of other code, and are not counted.", m)
        self.assertNotIn("compiled: 90 runners", m)

    def test_a_text_field_and_comments_are_not_code(self):
        # The source of the claims, a comment of the generated header and the indentation of its code
        # changed: the code did not, and every run still counts.
        before = self.measured("add_1_1")
        self.change("add_1_1", lambda k: k["source"].update(cite="the same bound, cited otherwise"))
        self.edit_file("include/kairn/gen/scalar.hpp", lambda t: t.replace(
            "// one rounding to nearest, the bound u/(1+u) of JR18.", "// another comment.", 1))
        self.edit_file("include/kairn/gen/scalar.hpp", lambda t: edit_definitions(
            t, "add_1_1", "    const double s = a + b;", "        const double s = a + b;  // a comment"))
        self.assertEqual(self.measured("add_1_1"), before)

    def test_a_changed_callee_changes_its_callers(self):
        # fast_two_sum's listing changed (its sum written b + a) and the headers printed again by the
        # generator, which inlines every call: the kernels that call it have other code; two_sum and
        # add_1_1, which do not, keep their runs.
        self.edit_file("gen/kernels/fast_two_sum.kernel", lambda t: t.replace("s = add(a, b)", "s = add(b, a)"))
        print_headers(self.copy.root)
        for name in ("fast_two_sum", "add_2_2", "add_fast_2_2", "mul_2_2"):
            self.assertIn("No stored brute-force run is of this kernel's code as it is now", self.measured(name))
        for name in ("ball_add_2", "add_2_2_full"):   # through add_2_2
            self.assertIn("No stored brute-force run is of this kernel's code as it is now", self.measured(name))
        for name in ("two_sum", "add_1_1", "lt_2_2"):
            m = self.measured(name)
            self.assertIn("**Milestone 1**", m)
            self.assertNotIn("other code", m)

    def test_a_changed_helper_changes_the_kernels_that_call_it(self):
        # A function of the prelude that kernels call by name (abs_bits) is part of their code.
        self.edit_file("include/kairn/gen/prelude.hpp", lambda t: t.replace(
            "& 0x7fffffffffffffffu);", "& 0x7fffffffffffffffull);", 1))
        self.assertIn("No stored brute-force run is of this kernel's code as it is now", self.measured("ball_add_2"))
        self.assertIn("**Milestone 1**", self.measured("add_1_1"))

    def test_a_kernel_that_no_run_judged(self):
        # One summary left, of add_2_2 alone: add_1_1's page says no run judged it.
        brute = self.copy.path("results/milestone2/brute")
        data = json.loads(reference.read(os.path.join(brute, "linux-x86-64.json")))
        data["compiled"]["kernels"] = {"add_2_2": data["compiled"]["kernels"]["add_2_2"]}
        data["interp"]["enumerations"] = [r for r in data["interp"]["enumerations"] if r["kernel"] == "add_2_2"]
        shutil.rmtree(self.copy.path("results/milestone1/brute"))
        shutil.rmtree(brute)
        os.makedirs(brute)
        with open(os.path.join(brute, "linux-x86-64.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)
        self.assertIn("No stored brute-force run has judged this kernel yet.", self.measured("add_1_1"))
        m = self.measured("add_2_2")
        self.assertIn("**Milestone 2**: the runs of commit `5f597fb`", m)
        self.assertIn("compiled: 36 runners on 1 machine |", m)
        self.assertNotIn("**Milestone 1**", m)
        self.assertNotIn("**In all**", m)

    def test_runs_that_judged_other_claims_are_left_out_of_the_total(self):
        # ball_add_2_full's claim gained its condition B4 after Milestone 1's main runs, of its code
        # now: the page shows them, flagged, and the total counts the supplementary run that judged
        # the condition and Milestone 2's.
        m = self.measured("ball_add_2_full")
        self.assertIn("**The condition of this claim was not judged by every run.**", m)
        self.assertIn("but for the rows that judged other claims, which are not counted", m)
        m1, m2 = table_rows(m, "**Milestone 1**"), table_rows(m, "**Milestone 2**")
        total = table_rows(m, "**In all**")
        title = "`binary64` (`double`), compiled"
        self.assertEqual(total[title + ", Milestone 1 and Milestone 2"][0],
                         m1[title + ", supplementary run: 60 runners on 3 machines"][0]
                         + m2[title + ": 90 runners on 3 machines"][0])

    def test_a_run_of_a_commit_without_fingerprints_fails(self):
        def drop(text):
            data = json.loads(text)
            del data["commits"]["5f597fbcf2a7f5b077671e115487bc9515c0bb24"]
            return json.dumps(data)
        self.edit_file("results/brute-code.json", drop)
        self.fails("results/milestone2/brute/", "5f597fb", "docs/tools/brute_code.py")


SYNTHETIC_PRELUDE = """// Generated.
#pragma once
namespace kairn::gen {
#if KAIRN_GEN_FIXUP_CALL
namespace fixup {
template <class T, int N>
struct result {
    T limb[N];
};
}  // namespace fixup
#endif
KAIRN_GEN_FORCEINLINE constexpr double abs_bits(double a) noexcept {
    return a;  // stands for the real one
}
}  // namespace kairn::gen
"""

SYNTHETIC_HEADER = """// Generated.
#pragma once
#include "prelude.hpp"

KAIRN_GEN_PUSH_WARNINGS
namespace kairn::gen {

// a(x) -> y
// A kernel with a fix-up of its own, that calls b by name.
#if KAIRN_GEN_FIXUP_CALL
namespace fixup {
KAIRN_GEN_COLD result<double, 1> a(double x) noexcept {
    return {{x}};
}
}  // namespace fixup
#endif
KAIRN_GEN_FORCEINLINE void a(double x, double& y_out) noexcept {
    const double t = b(x);  // a comment at the end of a line
    if (t > 0) [[likely]] {
        y_out = t;
    } else {
        y_out = fixup::a(x).limb[0];
    }
}

// b(x) -> y
KAIRN_GEN_FORCEINLINE double b(double x) noexcept { return x + 1.0; }

// c(x) -> y
KAIRN_GEN_FORCEINLINE void c(double x, double& y_out) noexcept {
    y_out = abs_bits(x);
}

// fold s
inline void s_seq(const double* x_in, std::size_t n, double& r_out) noexcept {
    double r = 0.0;
    for (std::size_t i_ = 0; i_ < n; ++i_) {
        c(x_in[i_], r);
    }
    r_out = r;
}

}  // namespace kairn::gen
KAIRN_GEN_POP_WARNINGS
"""


class BruteCode(unittest.TestCase):
    """docs/tools/brute_code.py: what the code of a kernel is, and the fingerprints of the stored
    runs' commits."""

    def prints(self, header=SYNTHETIC_HEADER, prelude=SYNTHETIC_PRELUDE):
        files = {"prelude": prelude, "scalar": header, "avx2": "", "neon": header}
        return reference.BRUTE_CODE.fingerprints(files, ["a", "b", "c", "d"], ["s"])

    def test_definitions(self):
        defs = reference.BRUTE_CODE.definitions(SYNTHETIC_HEADER, "test")
        self.assertEqual([n for n, _ in defs], ["a", "a", "b", "c", "s_seq"])
        self.assertEqual(defs[0][1], ("KAIRN_GEN_COLD result<double, 1> a(double x) noexcept {", "return {{x}};", "}"))
        self.assertIn("const double t = b(x);", defs[1][1])
        self.assertEqual(defs[2][1], ("KAIRN_GEN_FORCEINLINE double b(double x) noexcept { return x + 1.0; }",))
        self.assertEqual(reference.BRUTE_CODE.definitions(SYNTHETIC_PRELUDE, "test")[0][0], "abs_bits")

    def test_comments_blank_lines_and_indentation_are_not_code(self):
        other = SYNTHETIC_HEADER.replace("// A kernel with", "// Another kernel with").replace(
            "    const double t = b(x);  // a comment at the end of a line", "\n        const double t = b(x);")
        self.assertEqual(self.prints(other), self.prints())

    def test_a_changed_operation_changes_its_kernel_and_its_callers(self):
        before, after = self.prints(), self.prints(SYNTHETIC_HEADER.replace("x + 1.0", "x + 2.0"))
        self.assertNotEqual(before["b"], after["b"])
        self.assertNotEqual(before["a"], after["a"])   # a calls b by name
        self.assertEqual(before["c"], after["c"])
        self.assertEqual(before["s"], after["s"])
        self.assertIsNone(before["d"])                 # no header defines d

    def test_a_changed_helper_changes_the_functions_that_call_it(self):
        before, after = self.prints(), self.prints(prelude=SYNTHETIC_PRELUDE.replace("return a;", "return -a;"))
        self.assertNotEqual(before["c"], after["c"])
        self.assertNotEqual(before["s"], after["s"])   # the loop calls c by name
        self.assertEqual(before["a"], after["a"])
        self.assertEqual(before["b"], after["b"])

    def test_what_it_cannot_read_fails(self):
        with self.assertRaises(reference.BRUTE_CODE.CodeError):
            reference.BRUTE_CODE.definitions(SYNTHETIC_HEADER.replace(
                "void c(double x, double& y_out) noexcept {", "void c(double x,\n    double& y_out) noexcept {"), "test")
        with self.assertRaises(reference.BRUTE_CODE.CodeError):
            reference.BRUTE_CODE.definitions(SYNTHETIC_HEADER + "}\n", "test")
        # A function would be the code of two objects: the kernel s_seq and the loop s.
        with self.assertRaises(reference.BRUTE_CODE.CodeError):
            reference.BRUTE_CODE.fingerprints({"prelude": "", "scalar": SYNTHETIC_HEADER, "avx2": "", "neon": ""},
                                              ["s_seq"], ["s"])

    def test_the_fingerprints_have_every_commit_of_the_stored_runs(self):
        code = reference.BRUTE_CODE.load(ROOT)
        for commit, summaries in reference.BRUTE_CODE.summary_commits(ROOT).items():
            self.assertIn(commit, code, "%s, of %s" % (commit, summaries))

    def test_the_claims_a_run_judges(self):
        # The fingerprint of a kernel's claims leaves out where they come from, which theorem proves
        # them, whether it is proved, and the operation count; anything else is a claim.
        entry = json.loads(reference.read(os.path.join(ROOT, "gen", "claims.json")))["kernels"][0]
        fp = reference.BRUTE_CODE.claims_fingerprint
        for field in reference.BRUTE_CODE.NOT_JUDGED:
            changed = dict(entry)
            changed[field] = "something else"
            self.assertEqual(fp(changed), fp(entry), field)
        for field, value in (("min_precision", 99), ("requires", ["something"]), ("ensures", []),
                             ("inputs", []), ("domain", "other")):
            changed = dict(entry)
            changed[field] = value
            self.assertNotEqual(fp(changed), fp(entry), field)

    def test_the_fingerprints_are_what_the_history_gives(self):
        # Needs the commits of the stored runs: a shallow clone (the CI's checkout) has none.
        commits = reference.BRUTE_CODE.summary_commits(ROOT)
        if not all(reference.BRUTE_CODE.has_commit(ROOT, c) for c in commits):
            self.skipTest("the commits of the stored runs are not in this clone (a shallow one); "
                          "python3 docs/tools/brute_code.py --check needs them")
        self.assertEqual(reference.BRUTE_CODE.manifest(ROOT),
                         reference.read(os.path.join(ROOT, *reference.BRUTE_CODE.MANIFEST.split("/"))))


LEAD = re.compile(r"^\*\*(Milestone \d+|`[^`]+`)\*\*: ", re.M)


class Claims(unittest.TestCase):
    """Whether a stored run judged the claims a kernel has now, against the claims themselves. The
    claims a run judged are those of the commit its summary names as the code under test (the
    kernels and their claims: CODE_PATHS of tests/brute/brute.py include gen/), whose entry of
    gen/claims.json results/brute-code.json keeps as a fingerprint (brute_code.NOT_JUDGED left out),
    written from the history and checked against it above. The summaries themselves record the
    oracle's label and kind of every entry it judged, not the entry."""

    @classmethod
    def setUpClass(cls):
        cls.site = reference.Site(ROOT)
        cls.files = reference.plan(ROOT)
        cls.code = reference.BRUTE_CODE.load(ROOT)
        cls.now = {e["name"]: e for e in json.loads(reference.read(os.path.join(ROOT, "gen", "claims.json")))["kernels"]}

    def judged_now(self, d, name):
        fp = reference.BRUTE_CODE.claims_fingerprint(self.now[name])
        return all(self.code[c]["claims"].get(name) == fp for c in d["commit"])

    def runs(self, name):
        """[(campaign, [the summaries of the campaign that judged the kernel's code])]."""
        out = []
        for c in self.site.brute:
            docs = [d for d in c["docs"] + c["supplementary"]
                    if reference.judged_by(d, name) and self.site.same_code(d, name)]
            if docs:
                out.append((c, docs))
        return out

    def test_every_run_is_marked_by_the_claims_of_its_commit(self):
        # A page says that runs judged other claims exactly where the claims of their commit are not
        # the claims now: of every run of a campaign (the note), of some (the note and the rows marked
        # "other claims"), or of none (no word of it).
        blocks = mixed = other = 0
        for name in self.site.kernels:
            page = self.files["docs/reference/%s.md" % name]
            measured = page[page.index("## Measured"):page.index("## Not claimed")]
            leads = list(LEAD.finditer(measured))
            for c, docs in self.runs(name):
                title = self.site.campaign_title(c)
                i = [m.group(1) for m in leads].index(title)
                end = leads[i + 1].start() if i + 1 < len(leads) else len(measured)
                block = measured[leads[i].start():end].split("**In all**")[0]
                same = [self.judged_now(d, name) for d in docs]
                where = "%s, %s" % (name, title)
                if all(same):
                    self.assertNotIn("other claims", block, where)
                elif not any(same):
                    other += 1
                    self.assertIn("**These runs judged other claims.**", block, where)
                    self.assertNotIn("other claims:", block, where)
                else:
                    mixed += 1
                    self.assertIn("other claims:", block, where)
                    self.assertTrue("**The condition of this claim was not judged by every run.**" in block
                                    or "**Not every run below judged the claims above.**" in block, where)
                    for d, s in zip(docs, same):
                        self.assertIn("`%s`" % d["commit"][0][:7], block, where)
                blocks += 1
        # Milestone 1's main runs of the eight full Ball kernels judged their claims before B4 had its
        # condition, at the same code; every other run of the code now judged the claims now.
        self.assertGreaterEqual(blocks, 288)
        self.assertEqual((mixed, other), (8, 0))

    def test_the_oracle_labels_are_those_of_the_claims(self):
        # Where a run judged the claims now, the oracle's label of each entry is the one the page
        # prints for that claim (the whole label for the kinds of reference.LABELLED_KINDS, its start
        # for the others), and those of the core of a full kernel follow; where a run judged other
        # claims, the labels differ, or the page says that the claims differ where labels do not show.
        checked = 0
        for name, k in self.site.kernels.items():
            page = self.files["docs/reference/%s.md" % name]
            for c, docs in self.runs(name):
                for d in docs:
                    b = reference.brute_rows(name, [d], "")
                    for r in b["rows"]:
                        if not r["entries"]:
                            continue
                        ext = k.extended and b["extended"]
                        own = k.entry["ensures"] if ext else (k.finite_entries if k.finite_reading
                                                              else k.entry["ensures"])
                        got = [x["label"] for x in r["entries"]]
                        want = [k.label(e) for e in own]
                        where = "%s, %s, %s" % (name, d["_path"], r["key"])
                        if not self.judged_now(d, name):
                            self.assertTrue(got[:len(want)] != want or "what their labels do not show" in page, where)
                            continue
                        self.assertEqual([x["kind"] for x in r["entries"][:len(own)]], [e["kind"] for e in own], where)
                        for x, e in zip(r["entries"], own):
                            if reference.labelled(e):
                                self.assertEqual(x["label"], k.label(e), where)
                            else:
                                self.assertTrue(x["label"].startswith(k.label(e)), where)
                        core = next((e["core"] for e in own if e["kind"] == "extends"), None)
                        if ext and core:
                            self.assertEqual(got[len(own):], ["F2, core %s: %s" % (core, reference.entry_label(e))
                                                              for e in self.site.kernels[core].entry["ensures"]], where)
                        elif not ext:
                            self.assertEqual(len(got), len(own), where)
                        checked += 1
        self.assertGreater(checked, 1500)


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
