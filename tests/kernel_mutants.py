"""Faults planted in the generated scalar kernels, to see what the quick tier's samples catch next to
the full tier's, and what the generator's comparison with the interpreter catches that neither does
(docs/developer/testing.md, "Time").

    python3 tests/kernel_mutants.py [--jobs N] [--only KERNEL,...] [--ids m0000,...] [--cxx CXX]
                                    [--quick CROSSCHECK,API] [--full CROSSCHECK,API]
                                    [--bits CXX [CXX ...]] [--no-tiers]

Each mutant changes one statement of one kernel in a copy of include/kairn/gen/scalar.hpp, the same
statement of the kernel's double and float code (const T x = EXPR;); a statement of a fix-up, in both
of its forms (inline behind #else, and the function of the namespace fixup), since
KAIRN_GEN_FIXUP_CALL picks one. The changes:

    sign      the first + becomes -, or the first - becomes +
    drop      a op b becomes a
    fma0      fma_rn(a, b, c) becomes fma_rn(a, b, 0)
    textbook  fma_rn(a, b, 0) becomes a * b, the product of the contraction experiment
    unfused   fma_rn(a, b, c) becomes a * b + c
    cmp       > becomes >=, < becomes <=, == becomes !=
    const     a hexadecimal constant with a fraction loses its last hexadecimal digit
    select    c ? a : b becomes c ? b : a

For each, three scalar runners (gen/tests/runner.cpp) are built against the copy with CXX (a
GCC-style compiler; default c++) at -O3 -DNDEBUG, as Release builds them: as they stand, with
-ffp-contract=off and with -ffp-contract=fast; and the public interface's runner
(tests/api/runner.cpp). Then tests/crosscheck.py runs the three on the kernel's binary64 and
binary32 cases (seed 0), and the public interface's forms of the kernel, if it has any (seed 1), as
the tests of each tier do, guards included: by default 6000 and 2000 cases
for the quick tier, 20000 and 10000 for the full tier. A tier catches a mutant if one of its tests
fails. A mutant that does not compile is reported and left out. --no-tiers leaves all of this out.

--bits adds the generator's comparison with the interpreter (gen/tests/test_cxx.py,
Kernels.test_matrix), through that file's code: the scalar runner with a table of the mutant's
kernel alone, built with each compiler given in every configuration of the test's matrix (-O0 and
-O2, each contraction setting, with and without -frounding-math, both forms of the fix-ups: 15 per
compiler), each on the test's cases of the kernel, every result required to be bit-identical to the
interpreter's. The comparison catches a mutant if one build differs. A build that -Werror refuses is
built without it and noted (werror). Each mutant is then put in one class: caught by the quick
tier, by the full tier only, by the comparison only, or by nothing.

The kernels of the round-up interval ("rounding": "upward") are not in scalar.hpp, and the run above
leaves them out. --upward plants the faults in them instead (they require the rounding mode upward
set by kairn::upward::Scope and the options of docs/concepts/upward.md, GCC and Clang
-frounding-math, MSVC /fp:strict): each mutant changes one statement of the two-number form of
include/kairn/gen/upward.hpp, the form whose statements are those of the kernel's listing (the
register and array forms are compared with it and with the interpreter, bit for bit, by
gen/tests/test_upward_cxx.py), in its double and float code alike, with the changes above that
apply (sign, drop, cmp, and select, an arm of which may be a constant here: upselect) and these:

    neg       -a becomes a
    ne        != becomes ==
    logic     the first & becomes |, or the first | becomes &
    maxswap   a > b ? a : b (max_nl in MAXPD's form) becomes b > a ? b : a, the maximum that
              returns the NaN
    nan       quiet_NaN() becomes infinity()

Three runners of the family in the two-number form (gen/tests/upward_runner.cpp,
KAIRN_UPWARD_FORM_NUMBERS) are built against the copy with CXX at -O3 -DNDEBUG -frounding-math: as
they stand, with -ffp-contract=off and with -ffp-contract=fast; tests/crosscheck.py runs them on the
kernel's binary64 and binary32 cases (seed 0) as the tiers do, guards included: 2000 cases for the
quick tier and 20000 for the full tier (KAIRN_CROSSCHECK_INTERVAL_QUICK_CASES and
KAIRN_CROSSCHECK_CASES); the public type has no runner here. --bits adds the comparison of
test_upward_cxx.py: the two-number runner built with each compiler given at -O0 and -O2 under each
contraction setting, on that test's requests of the kernel, bit for bit the interpreter's (--max sel,
the form of a > b ? a : b).

Every applicable mutant runs, 1052 of the 63 kernels when this was written. With --jobs 32 --cxx g++
--bits g++ clang++, 47 minutes on 32 hardware threads of a 2019 x86-64 server (GCC 13, Clang 18):
865 caught by the full tier, 863 of them by the quick tier, 122 more by the comparison only, 65 by
nothing (results/milestone1/mutants/, from before the comparison's special operands, which catch 17
of the 65). Without --bits, about 20 minutes on an Apple M3 Max with --jobs 12. It prints a line per
mutant and a summary, and writes everything into results.json of its work directory (--work, default
a temporary directory), a line per mutant. Python's standard library and a C++ compiler; not
Windows.
"""
import argparse
import concurrent.futures as cf
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN_TESTS = os.path.join(ROOT, "gen", "tests")
STMT = re.compile(r"^(    const (?:double|float|bool) \w+ = )(.*);$")
FIXUP_STMT = re.compile(r"^(        const (?:double|float|bool) \w+ = )(.*);$")
# A kernel's function: KAIRN_GEN_FORCEINLINE, or inline for those of ordinary_inline (interval_mul_2);
# its first parameter may be [[maybe_unused]] (the radii of the ball vectors).
HEADER = re.compile(r"^(?:KAIRN_GEN_FORCEINLINE|inline) (?:constexpr )?void (\w+)\((?:\[\[maybe_unused\]\] )?"
                    r"(double|float) ")
FIXUP_HEADER = re.compile(r"^KAIRN_GEN_COLD (?:constexpr )?result<(double|float), \d+> (\w+)\(")
OPS = ("sign", "drop", "fma0", "textbook", "unfused", "cmp", "const", "select")
# The round-up interval (--upward): the two-number form of include/kairn/gen/upward.hpp, between
# "#if/#elif KAIRN_UPWARD_FORM == KAIRN_UPWARD_FORM_NUMBERS" and the next directive; a statement is
# "    [const] T x = EXPR;" (a value given to a barrier is not const).
UPWARD_HPP = os.path.join(ROOT, "include", "kairn", "gen", "upward.hpp")
UPWARD_RUNNER = os.path.join(GEN_TESTS, "upward_runner.cpp")
UP_REGION = re.compile(r"^#(?:el)?if KAIRN_UPWARD_FORM == KAIRN_UPWARD_FORM_NUMBERS\b")
UP_HEADER = re.compile(r"^KAIRN_GEN_FORCEINLINE void (upward_\w+_1)\((?:numbers<)?(double|float)\b")
UP_STMT = re.compile(r"^(    (?:const )?(?:double|float|bool) \w+ = )(.*);$")
UP_OPS = ("sign", "drop", "cmp", "upselect", "neg", "ne", "logic", "maxswap", "nan")
UP_NUMBERS = ["-frounding-math", "-DKAIRN_UPWARD_FORM=KAIRN_UPWARD_FORM_NUMBERS", "-DKAIRN_UPWARD_RUNNER_ARRAYS"]
# On x86-64 the headers need hardware FMA, which kairn::fma adds to the tests' runners (-mfma).
X86_FMA = ["-mfma"] if platform.machine().lower() in ("x86_64", "amd64") else []
# As tests/CMakeLists.txt: the kernels whose cross-checks do not fail on a suspicious result.
INTERMEDIATE_OVERFLOW = ("split", "two_prod_dekker")


def blocks(lines):
    """{kernel: {'double': (first, end), 'float': (first, end)}}: the lines of each function body;
    for a kernel with a fix-up also 'fixup double' and 'fixup float', the bodies of its functions
    in the namespace fixup."""
    out = {}
    i = 0
    while i < len(lines):
        m = HEADER.match(lines[i])
        f = FIXUP_HEADER.match(lines[i])
        if m or f:
            j = i + 1
            while lines[j] != "}":
                j += 1
            name, key = (m.group(1), m.group(2)) if m else (f.group(2), "fixup " + f.group(1))
            out.setdefault(name, {})[key] = (i + 1, j)
            i = j
        i += 1
    return out


def statements(lines, b, t):
    """The statements of the type-t code of a kernel that a mutant may change, as lists of line
    indices: one line for a statement of the body; for a statement of the fix-up, its line in the
    inline form (behind #else) and its line in the function of the namespace fixup, which hold the
    same text (KAIRN_GEN_FIXUP_CALL picks one form, so a mutant changes both)."""
    first, end = b[t]
    out = [[i] for i in range(first, end) if STMT.match(lines[i])]
    inline, inside = [], False
    for i in range(first, end):
        if lines[i] in ("#else", "#endif"):
            inside = lines[i] == "#else"
        elif inside and FIXUP_STMT.match(lines[i]):
            inline.append(i)
    if inline:
        ff, fe = b["fixup " + t]
        function = [i for i in range(ff, fe) if STMT.match(lines[i])]
        if [lines[i].strip() for i in inline] != [lines[i].strip() for i in function]:
            raise SystemExit("the two forms of the fix-up of a kernel differ (%s)" % lines[inline[0]])
        out += [list(p) for p in zip(inline, function)]
    return out


def mutate(expr, op):
    """EXPR changed by OP, or None where OP does not apply. ZERO stands for the type's zero."""
    if op == "sign":
        m = re.search(r" ([+-]) ", expr)
        return expr[:m.start(1)] + ("-" if m.group(1) == "+" else "+") + expr[m.end(1):] if m else None
    if op == "drop":
        m = re.fullmatch(r"(\w+) [+*-] (\w+)", expr)
        return m.group(1) if m else None
    if op == "fma0":
        m = re.fullmatch(r"fma_rn\(([^,]+), ([^,]+), ([^,]+)\)", expr)
        if not m or m.group(3) in ("0.0", "0.0f"):
            return None
        return "fma_rn(%s, %s, ZERO)" % (m.group(1), m.group(2))
    if op == "textbook":
        m = re.fullmatch(r"fma_rn\(([^,]+), ([^,]+), 0\.0f?\)", expr)
        return "%s * %s" % (m.group(1), m.group(2)) if m else None
    if op == "unfused":
        m = re.fullmatch(r"fma_rn\(([^,]+), ([^,]+), ([^,]+)\)", expr)
        return "(%s * %s + %s)" % m.groups() if m else None
    if op == "cmp":
        for a, b in ((" > ", " >= "), (" < ", " <= "), (" == ", " != ")):
            if a in expr:
                return expr.replace(a, b, 1)
        return None
    if op == "const":
        m = re.search(r"0x1\.([0-9a-f]+)p([+-]\d+)(f?)", expr)
        if not m:
            return None
        digits = m.group(1)[:-1]
        return expr[:m.start()] + "0x1%sp%s%s" % ("." + digits if digits else "", m.group(2),
                                                  m.group(3)) + expr[m.end():]
    if op == "select":
        m = re.fullmatch(r"(\w+) \? ([^:]+) : (.+)", expr)
        return "%s ? %s : %s" % (m.group(1), m.group(3), m.group(2)) if m else None
    if op == "upselect":
        # A selection of the round-up interval, whose arm may be a constant (std::...::quiet_NaN()).
        m = re.fullmatch(r"(\w+) \? (.+?) : (.+)", expr)
        return "%s ? %s : %s" % (m.group(1), m.group(3), m.group(2)) if m and " ? " not in m.group(3) else None
    if op == "neg":
        m = re.fullmatch(r"-(\w+)", expr)
        return m.group(1) if m else None
    if op == "ne":
        return expr.replace(" != ", " == ", 1) if " != " in expr else None
    if op == "logic":
        m = re.search(r" ([&|]) ", expr)
        return expr[:m.start(1)] + ("|" if m.group(1) == "&" else "&") + expr[m.end(1):] if m else None
    if op == "maxswap":
        m = re.fullmatch(r"(\w+) > (\w+) \? \1 : \2", expr)
        return "%s > %s ? %s : %s" % (m.group(2), m.group(1), m.group(2), m.group(1)) if m else None
    if op == "nan":
        return expr.replace("quiet_NaN()", "infinity()", 1) if "quiet_NaN()" in expr else None
    return None


def candidates(lines, b):
    """(statement, op, edits) of each mutant, edits being the (line index, new line) of the
    statement's double and float code (and of both forms of a fix-up's statement)."""
    def parts(i):
        return (STMT.match(lines[i]) or FIXUP_STMT.match(lines[i])).groups()

    out = []
    for j, (dl, fl) in enumerate(zip(statements(lines, b, "double"), statements(lines, b, "float"))):
        ed, ef = parts(dl[0])[1], parts(fl[0])[1]
        for op in OPS:
            nd, nf = mutate(ed, op), mutate(ef, op)
            if nd is None or nf is None or nd == ed:
                continue
            nd, nf = nd.replace("ZERO", "0.0"), nf.replace("ZERO", "0.0f")
            out.append((j, op, [(i, parts(i)[0] + nd + ";") for i in dl] + [(i, parts(i)[0] + nf + ";") for i in fl]))
    return out


def upward_blocks(lines, names):
    """{kernel: {'double': (first, end), 'float': (first, end)}}: the bodies of the two-number form
    of each kernel of NAMES in include/kairn/gen/upward.hpp."""
    out, inside, i = {}, False, 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#"):
            inside = bool(UP_REGION.match(line))
        elif inside:
            m = UP_HEADER.match(line)
            if m and m.group(1) in names:
                j = i + 1
                while lines[j] != "}":
                    j += 1
                out.setdefault(m.group(1), {})[m.group(2)] = (i + 1, j)
                i = j
        i += 1
    return out


def upward_candidates(lines, b):
    """(statement, op, edits) of each mutant of a kernel of the round-up interval: its two-number
    form's double and float statements, changed alike."""
    out = []
    double = [i for i in range(*b["double"]) if UP_STMT.match(lines[i])]
    single = [i for i in range(*b["float"]) if UP_STMT.match(lines[i])]
    if len(double) != len(single):
        raise SystemExit("the double and float code of a kernel differ (%s)" % lines[b["double"][0] - 1])
    for j, (dl, fl) in enumerate(zip(double, single)):
        pd, ed = UP_STMT.match(lines[dl]).groups()
        pf, ef = UP_STMT.match(lines[fl]).groups()
        for op in UP_OPS:
            nd, nf = mutate(ed, op), mutate(ef, op)
            if nd is None or nf is None or nd == ed:
                continue
            out.append((j, op, [(dl, pd + nd + ";"), (fl, pf + nf + ";")]))
    return out


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    return r.returncode


def bit_comparison(a, d, kernel):
    """The builds of the generator's comparison with the interpreter (gen/tests/test_cxx.py,
    Kernels.test_matrix: every flag set of its matrix, with each compiler of --bits) whose output
    on that test's cases of the kernel is not bit-identical to the interpreter's, each with the
    number of cases that differ; and the builds that -Werror refuses, which are then built without
    it. The runner is gen/tests/runner.cpp with a table of this kernel alone. None for the first
    if a build fails without -Werror too."""
    cases, want, text = a.expected[kernel]
    b = os.path.join(d, "bits")
    os.makedirs(b, exist_ok=True)
    shutil.copy(os.path.join(GEN_TESTS, "runner.cpp"), b)
    with open(os.path.join(b, "runner_kernels.inc"), "w") as f:
        f.write(a.table[kernel] + "\n")
    differ, werror, verdicts = [], [], {}
    for i, (label, cmd) in enumerate(a.test_cxx.configurations(a.bits)):
        exe = os.path.join(b, "runner%d" % i)
        src = ["-I", os.path.join(d, "include"), "-I", b, os.path.join(b, "runner.cpp"), "-o", exe]
        if run(cmd + src):
            werror.append(label)
            if run([c for c in cmd if c != "-Werror"] + src):
                return None, werror
        r = subprocess.run([exe], input=text, capture_output=True, text=True, timeout=600)
        if r.returncode:
            differ.append((label, len(cases)))
            continue
        if r.stdout not in verdicts:           # the same text as an already compared build
            try:
                verdicts[r.stdout] = len(a.test_cxx.differences(cases, want, r.stdout))
            except AssertionError:
                verdicts[r.stdout] = len(cases)
        if verdicts[r.stdout]:
            differ.append((label, verdicts[r.stdout]))
    return differ, werror


def upward_bit_comparison(a, d, kernel):
    """The builds of test_upward_cxx.py's comparison, the two-number form (with each compiler of
    --bits, at -O0 and -O2 under each contraction setting, -frounding-math), whose output on that
    test's requests of the kernel is not the interpreter's (--max sel), with the number of lines
    that differ; and the builds that -Werror refuses, built without it. None for the first if a build
    fails without -Werror too."""
    lines, want = a.expected[kernel]
    differ, werror = [], []
    for i, cxx in enumerate(a.bits):
        for level in ("-O0", "-O2"):
            for c in ("off", "on", "fast"):
                label = "%s %s -ffp-contract=%s" % (cxx, level, c)
                exe = os.path.join(d, "bits%d%s%s" % (i, level, c))
                cmd = [cxx] + a.test_upward_cxx.BASE + [level, "-ffp-contract=" + c] + UP_NUMBERS
                src = ["-I", os.path.join(d, "include"), "-I", GEN_TESTS, UPWARD_RUNNER, "-o", exe]
                if run(cmd + src):
                    werror.append(label)
                    if run([x for x in cmd if x != "-Werror"] + src):
                        return None, werror
                r = subprocess.run([exe], input="\n".join(lines) + "\n", capture_output=True, text=True,
                                   timeout=600)
                n = len(lines) if r.returncode else len(a.test_upward_cxx.differences(want, r.stdout, len(lines)))
                if n:
                    differ.append((label, n))
    return differ, werror


def tiers(a, d, kernel, res):
    """Whether the mutant compiles; res['quick'] and res['full'], the tests of each tier it fails."""
    base = [a.cxx, "-std=c++20", "-O3", "-DNDEBUG", "-w", "-I", os.path.join(d, "include")] + X86_FMA
    if a.upward:
        base += UP_NUMBERS
    runners = []
    for label, extra in (("cxx", []), ("cxx-contract-off", ["-ffp-contract=off"]),
                         ("cxx-contract-fast", ["-ffp-contract=fast"])):
        exe = os.path.join(d, label)
        source = UPWARD_RUNNER if a.upward else os.path.join(GEN_TESTS, "runner.cpp")
        if run(base + extra + ["-I", GEN_TESTS, source, "-o", exe]):
            return False
        runners += ["--runner", ("upward-numbers" + label[3:]) if a.upward else label, exe]
    forms = []
    if not a.upward:
        api = os.path.join(d, "api")
        if run(base + [os.path.join(ROOT, "tests", "api", "runner.cpp"), "-o", api]):
            return False
        forms = subprocess.run([api, "--forms", kernel], capture_output=True, text=True).stdout.split()
    suspicious = [] if kernel in INTERMEDIATE_OVERFLOW else ["--fail-on-suspicious"]
    driver = [sys.executable, os.path.join(ROOT, "tests", "crosscheck.py")]
    for tier, (n, napi) in (("quick", a.quick), ("full", a.full)):
        failed = []
        for fmt in ("binary64", "binary32"):
            if run(driver + ["compiled", "--kernel", kernel, "--format", fmt, "--seed", "0", "--count", str(n),
                             "--summary", os.path.join(d, "%s.%s.json" % (tier, fmt))] + suspicious + runners):
                failed.append("crosscheck." + fmt)
            if forms and run(driver + ["api", "--kernel", kernel, "--format", fmt, "--seed", "1",
                                       "--count", str(napi), "--summary-dir", os.path.join(d, "api-" + tier),
                                       "--runner", "build", api]):
                failed.append("api." + fmt)
        res[tier] = failed
    return True


def one(a, mid, kernel, j, op, edits, lines):
    d = os.path.join(a.work, mid)
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "include"), os.path.join(d, "include"))
    new = list(lines)
    for i, text in edits:
        new[i] = text
    header = "upward.hpp" if a.upward else "scalar.hpp"
    with open(os.path.join(d, "include", "kairn", "gen", header), "w") as f:
        f.write("\n".join(new) + "\n")
    res = {"id": mid, "kernel": kernel, "op": op, "stmt": j, "fixup": len(edits) == 4,
           "before": lines[edits[0][0]].strip(), "line": edits[0][1].strip(), "compiled": False}
    if a.tiers and not tiers(a, d, kernel, res):
        return res
    if a.bits:
        differ, werror = (upward_bit_comparison if a.upward else bit_comparison)(a, d, kernel)
        if differ is None:
            return res
        # Per compiler (by its file name), the number of its builds that differ (or that -Werror
        # refuses), and the largest number of cases that differ in one build.
        res["bits"] = {os.path.basename(c): n for c in a.bits
                       for n in [len([x for x, _ in differ if x.split()[0] == c])] if n}
        res["bits_cases"] = max((n for _, n in differ), default=0)
        res["werror"] = {os.path.basename(c): n for c in a.bits
                         for n in [len([x for x in werror if x.split()[0] == c])] if n}
    res["compiled"] = True
    shutil.rmtree(d, ignore_errors=True)
    return res


def classify(r):
    """The first of: caught by the quick tier, by the full tier only, by the bit comparison only,
    by nothing."""
    if r.get("quick"):
        return "quick"
    if r.get("full"):
        return "full only"
    return "bits only" if r.get("bits") else "nothing"


def pair(text):
    n = tuple(int(x) for x in text.split(","))
    if len(n) != 2:
        raise argparse.ArgumentTypeError("two numbers: cases of the cross-checks, cases of the API")
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="mutants at once")
    ap.add_argument("--only", help="comma-separated kernels")
    ap.add_argument("--ids", help="comma-separated mutants (m0000, ...), as a run of all numbers them")
    ap.add_argument("--cxx", default="c++", help="a GCC-style C++ compiler (default c++)")
    ap.add_argument("--quick", type=pair, default=(6000, 2000), help="cases of the quick tier")
    ap.add_argument("--full", type=pair, default=(20000, 10000), help="cases of the full tier")
    ap.add_argument("--bits", nargs="+", metavar="CXX",
                    help="also the generator's comparison with the interpreter, with these compilers")
    ap.add_argument("--no-tiers", dest="tiers", action="store_false", help="without the tiers' tests")
    ap.add_argument("--upward", action="store_true",
                    help="the kernels of the round-up interval, in the two-number form of gen/upward.hpp")
    ap.add_argument("--work", help="where to build and to write results.json")
    a = ap.parse_args()
    if a.upward:
        # The tiers' cases of the family (KAIRN_CROSSCHECK_INTERVAL_QUICK_CASES, KAIRN_CROSSCHECK_CASES);
        # it has no runner of the public interface here.
        a.quick = (2000, 0) if a.quick == (6000, 2000) else a.quick
        a.full = (20000, 0) if a.full == (20000, 10000) else a.full
    a.work = os.path.abspath(a.work or tempfile.mkdtemp(prefix="kairn-kernel-mutants-"))
    os.makedirs(a.work, exist_ok=True)
    with open(UPWARD_HPP if a.upward else os.path.join(ROOT, "include", "kairn", "gen", "scalar.hpp")) as f:
        lines = f.read().split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    with open(os.path.join(ROOT, "gen", "claims.json")) as f:
        claims = json.load(f)["kernels"]
    # The kernels of the round-up interval are not in scalar.hpp: --upward runs theirs, and the default
    # run leaves them out.
    names = [k["name"] for k in claims if (k.get("rounding") == "upward") == a.upward]
    if a.upward:
        bl = upward_blocks(lines, set(names))
        found = [(k,) + c for k in names for c in upward_candidates(lines, bl[k])]
    else:
        bl = blocks(lines)
        found = [(k,) + c for k in names for c in candidates(lines, bl[k])]
    jobs = [("m%04d" % i,) + job for i, job in enumerate(found)]
    jobs = [job for job in jobs if (not a.only or job[1] in a.only.split(","))
            and (not a.ids or job[0] in a.ids.split(","))]
    if a.bits and a.upward:
        # The requests of test_upward_cxx.py's comparison and the interpreter's lines, once per kernel.
        sys.path.insert(0, GEN_TESTS)
        import test_upward_cxx
        a.test_upward_cxx = test_upward_cxx
        every = test_upward_cxx.requests(0)
        a.expected = {}
        for k in sorted({job[1] for job in jobs}):
            mine = [line for line in every if line.split(" ", 1)[0] == k]
            a.expected[k] = (mine, test_upward_cxx.interpret(mine, "sel"))
    elif a.bits:
        # The cases of Kernels.test_matrix and the interpreter's results, once per kernel.
        sys.path.insert(0, GEN_TESTS)
        import common
        import test_cxx
        ks = common.kernels()
        a.test_cxx = test_cxx
        with open(os.path.join(GEN_TESTS, "runner_kernels.inc")) as f:
            a.table = {m.group(1): m.group(0) for m in re.finditer(r"^KAIRN_RUNNER_KERNEL\((\w+),.*$", f.read(), re.M)}
        a.expected = {}
        for k in sorted({job[1] for job in jobs}):
            cases = test_cxx.matrix_cases(ks, k)
            a.expected[k] = (cases, test_cxx.expect(None, cases), "".join(c[3] + "\n" for c in cases))
    results = []
    with cf.ThreadPoolExecutor(max(1, a.jobs)) as ex:
        futs = [ex.submit(one, a, *job, lines) for job in jobs]
        for fu in cf.as_completed(futs):
            r = fu.result()
            results.append(r)
            head = "%s %-20s %-8s statement %2d " % (r["id"], r["kernel"], r["op"], r["stmt"])
            if not r["compiled"]:
                print(head + " does not compile", flush=True)
                continue
            if a.tiers:
                head += " quick %-40s full %-40s" % (",".join(r["quick"]) or "-", ",".join(r["full"]) or "-")
            if a.bits:
                head += " bits: %d builds differ" % sum(r["bits"].values())
            print(head, flush=True)
    results.sort(key=lambda r: r["id"])
    for r in results:
        if r["compiled"]:
            r["class"] = classify(r)
    with open(os.path.join(a.work, "results.json"), "w") as f:
        f.write("[\n" + ",\n".join(json.dumps(r) for r in results) + "\n]\n")     # a line per mutant
    ok = [r for r in results if r["compiled"]]
    print("mutants: %d, compiled: %d; results in %s" % (len(results), len(ok), os.path.join(a.work, "results.json")))
    if a.tiers:
        full = [r for r in ok if r["full"]]
        quick = [r for r in ok if r["quick"]]
        print("caught by the full tier: %d, by the quick tier: %d; only by the full tier: %d, only by the quick "
              "tier: %d" % (len(full), len(quick), len([r for r in full if not r["quick"]]),
                            len([r for r in quick if not r["full"]])))
        for r in full:
            if not r["quick"]:
                print("  only the full tier: %s %s %s, statement %d: %s (%s)" % (
                    r["id"], r["kernel"], r["op"], r["stmt"], r["line"], ", ".join(r["full"])))
    if a.bits:
        print("differ from the interpreter in a build of the generator's matrix: %d"
              % len([r for r in ok if r["bits"]]))
        if a.tiers:
            print("; ".join("%s: %d" % (c, len([r for r in ok if r["class"] == c]))
                            for c in ("quick", "full only", "bits only", "nothing")))
        for r in ok:
            if not r["bits"] and (not a.tiers or r["class"] == "nothing"):
                print("  caught by nothing: %s %s %s, statement %d: %s -> %s" % (
                    r["id"], r["kernel"], r["op"], r["stmt"], r["before"], r["line"]))


if __name__ == "__main__":
    main()

