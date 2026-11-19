"""Faults planted in the generated scalar kernels, to see what the quick tier's samples catch next to
the full tier's (docs/developer/testing.md, "Time").

    python3 tests/kernel_mutants.py [--jobs N] [--only KERNEL,...] [--cxx CXX]
                                    [--quick CROSSCHECK,API] [--full CROSSCHECK,API]

Each mutant changes one statement of one kernel in a copy of include/kairn/gen/scalar.hpp, the same
statement of the kernel's double and float code (const T x = EXPR;), by one of these changes:

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
(tests/api/runner.cpp). Then tests/crosscheck.cmake runs the three on the kernel's binary64 and
binary32 cases (seed 0) and tests/api/pipeline.cmake the public interface's forms of the kernel, if
it has any (seed 1), as the tests of each tier do, guards included: by default 6000 and 2000 cases
for the quick tier, 20000 and 10000 for the full tier. A tier catches a mutant if one of its tests
fails. A mutant that does not compile is reported and left out.

Every applicable mutant runs, 1052 of the 63 kernels when this was written: about 20 minutes on an
Apple M3 Max with --jobs 12 (863 caught by the full tier, 861 of them by the quick tier). It prints a line per mutant and a summary, and writes everything into
results.json of its work directory (--work, default a temporary directory). Python's standard
library, cmake and a C++ compiler; not Windows.
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STMT = re.compile(r"^(    const (?:double|float|bool) \w+ = )(.*);$")
HEADER = re.compile(r"^KAIRN_GEN_FORCEINLINE (?:constexpr )?void (\w+)\((double|float) ")
OPS = ("sign", "drop", "fma0", "textbook", "unfused", "cmp", "const", "select")
# As tests/CMakeLists.txt: the kernels whose cross-checks do not fail on a suspicious result.
INTERMEDIATE_OVERFLOW = ("split", "two_prod_dekker")


def blocks(lines):
    """{kernel: {'double': (first, end), 'float': (first, end)}}: the lines of each function body."""
    out = {}
    i = 0
    while i < len(lines):
        m = HEADER.match(lines[i])
        if m:
            j = i + 1
            while lines[j] != "}":
                j += 1
            out.setdefault(m.group(1), {})[m.group(2)] = (i + 1, j)
            i = j
        i += 1
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
    return None


def candidates(lines, b):
    """(statement, op, double line index, new line, float line index, new line) of each mutant."""
    (ds, de), (fs, fe) = b["double"], b["float"]
    dst = [i for i in range(ds, de) if STMT.match(lines[i])]
    fst = [i for i in range(fs, fe) if STMT.match(lines[i])]
    out = []
    for j, (di, fi) in enumerate(zip(dst, fst)):
        md, mf = STMT.match(lines[di]), STMT.match(lines[fi])
        for op in OPS:
            nd, nf = mutate(md.group(2), op), mutate(mf.group(2), op)
            if nd is None or nf is None or nd == md.group(2):
                continue
            nd, nf = nd.replace("ZERO", "0.0"), nf.replace("ZERO", "0.0f")
            out.append((j, op, di, md.group(1) + nd + ";", fi, mf.group(1) + nf + ";"))
    return out


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    return r.returncode


def one(a, mid, kernel, j, op, di, dline, fi, fline, lines):
    d = os.path.join(a.work, mid)
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "include"), os.path.join(d, "include"))
    new = list(lines)
    new[di], new[fi] = dline, fline
    with open(os.path.join(d, "include", "kairn", "gen", "scalar.hpp"), "w") as f:
        f.write("\n".join(new) + "\n")
    res = {"id": mid, "kernel": kernel, "op": op, "stmt": j, "line": dline.strip(), "compiled": False}
    base = [a.cxx, "-std=c++20", "-O3", "-DNDEBUG", "-w", "-I", os.path.join(d, "include")]
    runners = []
    for label, extra in (("cxx", []), ("cxx-contract-off", ["-ffp-contract=off"]),
                         ("cxx-contract-fast", ["-ffp-contract=fast"])):
        exe = os.path.join(d, label)
        if run(base + extra + ["-I", os.path.join(ROOT, "gen", "tests"),
                               os.path.join(ROOT, "gen", "tests", "runner.cpp"), "-o", exe]):
            return res
        runners.append("%s|%s" % (label, exe))
    api = os.path.join(d, "api")
    if run(base + [os.path.join(ROOT, "tests", "api", "runner.cpp"), "-o", api]):
        return res
    res["compiled"] = True
    forms = subprocess.run([api, "--forms", kernel], capture_output=True, text=True).stdout.split()
    suspicious = "OFF" if kernel in INTERMEDIATE_OVERFLOW else "ON"
    for tier, (n, napi) in (("quick", a.quick), ("full", a.full)):
        failed = []
        for fmt in ("binary64", "binary32"):
            if run(["cmake", "-DPYTHON=" + sys.executable, "-DSOURCE_DIR=" + ROOT, "-DKERNEL=" + kernel,
                    "-DFORMAT=" + fmt, "-DFAIL_ON_SUSPICIOUS=" + suspicious, "-DCOUNT=%d" % n, "-DSEED=0",
                    "-DRUNNERS=" + "|".join(runners),
                    "-DSUMMARY=" + os.path.join(d, "%s.%s.json" % (tier, fmt)),
                    "-P", os.path.join(ROOT, "tests", "crosscheck.cmake")]):
                failed.append("crosscheck." + fmt)
            if forms and run(["cmake", "-DPYTHON=" + sys.executable, "-DSOURCE_DIR=" + ROOT,
                              "-DKERNEL=" + kernel, "-DFORMAT=" + fmt, "-DCOUNT=%d" % napi, "-DSEED=1",
                              "-DRUNNERS=build|" + api, "-DSUMMARY_DIR=" + os.path.join(d, "api-" + tier),
                              "-P", os.path.join(ROOT, "tests", "api", "pipeline.cmake")]):
                failed.append("api." + fmt)
        res[tier] = failed
    shutil.rmtree(d, ignore_errors=True)
    return res


def pair(text):
    n = tuple(int(x) for x in text.split(","))
    if len(n) != 2:
        raise argparse.ArgumentTypeError("two numbers: cases of the cross-checks, cases of the API")
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="mutants at once")
    ap.add_argument("--only", help="comma-separated kernels")
    ap.add_argument("--cxx", default="c++", help="a GCC-style C++ compiler (default c++)")
    ap.add_argument("--quick", type=pair, default=(6000, 2000), help="cases of the quick tier")
    ap.add_argument("--full", type=pair, default=(20000, 10000), help="cases of the full tier")
    ap.add_argument("--work", help="where to build and to write results.json")
    a = ap.parse_args()
    a.work = os.path.abspath(a.work or tempfile.mkdtemp(prefix="kairn-kernel-mutants-"))
    os.makedirs(a.work, exist_ok=True)
    with open(os.path.join(ROOT, "include", "kairn", "gen", "scalar.hpp")) as f:
        lines = f.read().split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    with open(os.path.join(ROOT, "gen", "claims.json")) as f:
        names = [k["name"] for k in json.load(f)["kernels"]]
    bl = blocks(lines)
    jobs = [(k,) + c for k in names if not a.only or k in a.only.split(",") for c in candidates(lines, bl[k])]
    results = []
    with cf.ThreadPoolExecutor(max(1, a.jobs)) as ex:
        futs = [ex.submit(one, a, "m%04d" % i, *job, lines) for i, job in enumerate(jobs)]
        for fu in cf.as_completed(futs):
            r = fu.result()
            results.append(r)
            if r["compiled"]:
                print("%s %-20s %-8s statement %2d  quick %-40s full %s" % (
                    r["id"], r["kernel"], r["op"], r["stmt"], ",".join(r["quick"]) or "-",
                    ",".join(r["full"]) or "-"), flush=True)
            else:
                print("%s %-20s %-8s statement %2d  does not compile" % (
                    r["id"], r["kernel"], r["op"], r["stmt"]), flush=True)
    results.sort(key=lambda r: r["id"])
    with open(os.path.join(a.work, "results.json"), "w") as f:
        json.dump(results, f, indent=1)
    ok = [r for r in results if r["compiled"]]
    full = [r for r in ok if r["full"]]
    quick = [r for r in ok if r["quick"]]
    print("mutants: %d, compiled: %d; caught by the full tier: %d, by the quick tier: %d; only by the "
          "full tier: %d, only by the quick tier: %d; results in %s" % (
              len(results), len(ok), len(full), len(quick), len([r for r in full if not r["quick"]]),
              len([r for r in quick if not r["full"]]), os.path.join(a.work, "results.json")))
    for r in full:
        if not r["quick"]:
            print("  only the full tier: %s %s %s, statement %d: %s (%s)" % (
                r["id"], r["kernel"], r["op"], r["stmt"], r["line"], ", ".join(r["full"])))


if __name__ == "__main__":
    main()
